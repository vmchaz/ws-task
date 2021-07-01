import aiohttp
import asyncio
import os
import time
import concurrent

cDEBUG_PRINT=False
cRETRY_STATUSES=[429]

class DownloadTask:
    DEFAULT = 0
    IN_PROGRESS = 1
    SUCCESS = 2
    FAILURE = 3
    
    def __init__(self, address, attempts=1):
        self.address = address
        self.retry_count = attempts
        self.task_status = DownloadTask.DEFAULT
        self.status = 0
        self.data = None
        
    def update_status(self, new_status):
        self.status = new_status
        
    def decrease_retry_count(self):
        if self.retry_count > 0:
            self.retry_count -= 1

    def get_address(self):
        return self.address


class TaskList:
    def __init__(self):
        self.tasks = []
        self.allow_duplicates = False
        self.finished_tasks = []
        self.failed_tasks = []
        
    def get_task(self):
        #print(len(self.tasks))
        return self.tasks.pop(0)
        
    def add_task(self, task):
        if (self.allow_duplicates) or ((not self.allow_duplicates) and (task not in self.tasks)):
            self.tasks.append(task)
        
    def is_empty(self):
        return len(self.tasks) == 0


async def async_worker(tl, delay, init_proc, deinit_proc, handler_proc, handler_arg, proc_num, worker_num):
    if cDEBUG_PRINT:
        print(f"Worker #{worker_num} started working")
    try:
        await init_proc(proc_num, worker_num, tl, handler_arg)
    except Exception as E:
        print(type(E), E)

    while not tl.is_empty():
        dt = tl.get_task()
        dt.decrease_retry_count()
        address = dt.get_address()
        ltime = time.time()
        if cDEBUG_PRINT:        
            print(f"Worker proc{proc_num}#{worker_num} started downloading {address} at time {ltime}")
        
        try:
            total_timeout = aiohttp.ClientTimeout(total=3)
            async with aiohttp.ClientSession(timeout=total_timeout) as session:
                async with session.get(address) as response:
                    if cDEBUG_PRINT:
                        print(f"Worker proc{proc_num}#{worker_num} got response status:", response.status)

                    http_response = await response.read()
                    if cDEBUG_PRINT:
                        print(f"Worker proc{proc_num}#{worker_num} finished downloading ", address)
                        
                    dt.status = response.status

                    if response.status not in cRETRY_STATUSES:
                        await handler_proc(proc_num, worker_num, response.status, http_response, dt, handler_arg)
                    else:
                        if dt.retry_count > 0:
                            print("Adding task ", dt.address, "to the end of the queue... (retries:", dt.retry_count, ")")                            
                            tl.add_task(dt)
                        else:
                            print(f"Download task {dt.address} failed")
                            tl.failed_tasks.append(dt)

        except (concurrent.futures._base.TimeoutError, asyncio.exceptions.TimeoutError) as E:
            print("Timeout while downloading", address)
            dt.status = 408
            if dt.retry_count > 0:
                print("Adding task ", dt.address, " to the end of the queue... (retries:", dt.retry_count, ")")
                tl.add_task(dt)
            else:
                print(f"Download task {dt.address} failed")
                tl.failed_tasks.append(dt)
                    
        except (aiohttp.client_exceptions.ClientOSError, aiohttp.client_exceptions.ServerDisconnectedError, 
            aiohttp.client_exceptions.ClientPayloadError) as E:
            print("Exception while downloading", address)
            print("Exception type", type(E))

            if dt.retry_count > 0:
                print("Adding task ", dt.address, "to the end of the queue... (retries:", dt.retry_count, ")")
                tl.add_task(dt)
            else:
                print(f"Download task {dt.address} failed")
                tl.failed_tasks.append(dt)
            
        except aiohttp.client_exceptions.InvalidURL as E:
            print("Exception while downloading", address)
            print("Exception type", type(E))
            print(f"Download task {dt.address} failed")
            tl.failed_tasks.append(dt)
        
        ltime = time.time()
        if cDEBUG_PRINT:
            print(f"Worker proc{proc_num}#{worker_num} finished processing {address} at time {ltime}")
            
        if delay:
            time.sleep(delay/1000)
            
    await deinit_proc(proc_num, worker_num, tl, handler_arg)
    if cDEBUG_PRINT:
        print(f"Worker proc{proc_num}#{worker_num} finished working")
    

def run_download_loop(workers_count, tasklist, process_num, delay, init_proc, deinit_proc, handler_proc, handler_tag):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError as E:
        loop = asyncio.new_event_loop()

    tasks = [async_worker(tasklist, delay, init_proc, deinit_proc, handler_proc, handler_tag, process_num, i) for i in range(workers_count)]
    wait_tasks = asyncio.wait(tasks)
    loop.run_until_complete(wait_tasks)
