from multiprocessing import Process, Queue
import asyncio
import psycopg2
import sys
import time
import os
from asyncworkers import DownloadTask, TaskList, async_worker, run_download_loop


cPROCESS_COUNT = int(os.environ.get("PROC_COUNT", "1"))
cASYNCWORKERS_COUNT = int(os.environ.get("ASYNCWORKERS_COUNT", "1"))
cDELAY = int(os.environ.get("DELAY_BETWEEN_QUERIES", "1"))
cATTEMPTS = 3

cINDEXSTART = 1000000
cINDEXEND = 1500000


cUSER = os.environ.get("POSTGRES_USER", "postgres_user")
cPASS = os.environ.get("POSTGRES_PASSWORD", "postgres_pass")
cDBSERVER = os.environ.get("POSTGRES_SERVER", "localhost")
cDBPORT = os.environ.get("POSTGRES_PORT", 5432)
cDBNAME = os.environ.get("POSTGRES_DBNAME", "tmpdb")





class DataObject:
    def __init__(self):
        self.queue = None
        

class DownloadTaskWildberries(DownloadTask):
    def get_address(self):
        a = f"https://napi.wildberries.ru/api/catalog/{self.address}/detail.aspx?_app-type=sitemobile&targetUrl=SG"
        return a


async def init_proc(proc_num, worker_num, task_list, data_obj):
    pass


async def deinit_proc(proc_num:int, worker_num:int, task_list:TaskList, data_obj:DataObject):
    pass


async def handler_proc(proc_num, worker_num, http_status, http_response, download_task, data_obj:DataObject):
    data_obj.queue.put((http_status, download_task.address, http_response))


def db_proc_base(queue):
    data_obj = DataObject()
       
    insert_req = "INSERT INTO items(id, description, status) VALUES(%s, %s, %s);"
    update_req = "UPDATE items SET description=%s, status=%s WHERE id=%s"
    
    try:
        print("Engine: Connecting to {}:{}@{}:{}/{}".format(cUSER, cPASS, cDBSERVER, cDBPORT, cDBNAME))
        connection = psycopg2.connect(user=cUSER, password=cPASS, host=cDBSERVER, port=cDBPORT, dbname=cDBNAME)
        cursor = connection.cursor()

        stop_flag = False
        while not stop_flag:
            queue_event = queue.get()
            if queue_event:
                status, item_id, item_json = queue_event
                
                print("Engine: Downloading item {} finished with status code {}".format(item_id, status))
                item_json_str = item_json.decode() if item_json else ""
                
                try:
                    cursor.execute(insert_req, (item_id, item_json_str, status))
                    connection.commit()
                    
                except (psycopg2.errors.UniqueViolation, psycopg2.errors.InFailedSqlTransaction) as E:
                    connection.rollback()
                    
                    cursor.execute(update_req, (item_json_str, status, item_id))
                    connection.commit()

            else:
                stop_flag = True
            
    except Exception as E:
        print(type(E), E)


def mp_proc_base(queue, queue_res, proc_num):
    data_obj = DataObject()
    data_obj.queue = queue_res

    stop_flag = False

    tasklist = TaskList()


    while not stop_flag:
        queueEvent = queue.get()
        if queueEvent:
            first_n = queueEvent[0]
            last_n = queueEvent[1]

            for i in range(first_n, last_n+1):
                tasklist.add_task(DownloadTaskWildberries(i, attempts=cATTEMPTS))

            proc_id = os.getpid()
            print(f"Proc#{proc_num} ({proc_id}) Processing interval", first_n, last_n)

            run_download_loop(cASYNCWORKERS_COUNT, tasklist, proc_num, cDELAY, init_proc, deinit_proc, handler_proc, data_obj)
            
            for ft in tasklist.failed_tasks:
                queue_res.put( (ft.status, ft.address, None) )

        else:
            queue.put(None)
            stop_flag = True


gFlags = {}        
gAddress = ""


# async def prepare_db():
#     print("Preparing database...")
#     conn = await asyncpg.connect('postgresql://postgres_user:rrs@localhost:5434/tmpdb')
#     await conn.execute('''CREATE TABLE IF NOT EXISTS public.items (
#     id integer,
#     description text,
#     status integer)''')


# async def prepare_pool():
#     cp = await asyncpg.create_pool()
#     async with cp.acquire() as conn:
#         r = await conn.fetchrow('select 1, 2, 3')
#         print(r)
#     return cp


def main():
    print("Engine:")
    print("ProcCount=", cPROCESS_COUNT)
    print("WorkersCount=", cASYNCWORKERS_COUNT)
    print("Delay=", cDELAY)
    arg1 = None



# CREATE TABLE IF NOT EXIST
#         INSERT INTO items(id, description) VALUES($1, $2)
#     ''', tmp_id, tmp_desc)


    queue = Queue()
    queue_res = Queue()

    processes = []

    for i in range(cPROCESS_COUNT):
        p = Process(target=mp_proc_base, args=(queue, queue_res, i))
        processes.append(p)

    db_process = Process(target=db_proc_base, args=(queue_res,))
    #processes.append(p)

    block_size = 100
    block_count = (cINDEXEND - cINDEXSTART) // block_size
    if block_count == 0:
        block_count = 1

    for i in range(block_count):
        start_num = cINDEXSTART + i*block_size
        end_num = cINDEXSTART + i*block_size + block_size - 1
        if end_num > cINDEXEND:
            end_num = cINDEXEND;
        queue.put((start_num, end_num))

    queue.put(None)


    ltime = time.time()

    for p in processes:
        p.start()

    db_process.start()

    for p in processes:
        p.join()

    queue_res.put(None)

    db_process.join()


    #run_download_loop(4, tasklist, handler_proc, arg1)
    ltime2 = time.time()
    print("DTime=", ltime2-ltime)

if __name__ == "__main__":
    main()
