from __future__ import print_function
import time
import boto3
import MySQLdb
from config import *

sqs = boto3.resource('sqs')
s3 = boto3.resource('s3')
queue = sqs.get_queue_by_name(QueueName=glacier_sqs)
query = "SELECT * FROM users WHERE username=%s"


# get a single job detail from dynamodb
def __get_detail__(jobid):
    ddb = boto3.resource('dynamodb')
    table = ddb.Table(dynamodb_table)

    res = table.get_item(Key={'job_id': jobid})
    job = res['Item']
    return job


# check whether an object in s3 exists
def __check_exist__(bucket, key):
    obj = s3.Object(result_bucket, filename)
    try:
        obj.load()
    except Exception as e:
        print(filename, e)
        return False
    else:
        return True


# move a S3 object
def __move_object__(oldbucket, oldkey, newbucket, newkey):
    try:
        s3.Object(newbucket, newkey).copy_from(CopySource=oldbucket + '/' + oldkey)
        s3.Object(newbucket, newkey).delete()
    except Exception as e:
        print(e)
        return False
    else:
        return True


while True:
    # print("Asking SQS for up to 10 messages...")
    # Get messages
    messages = queue.receive_messages(MaxNumberOfMessages=10, WaitTimeSeconds=20)

    # If a message was read, extract job parameters from the message body
    if len(messages) > 0:
        print("Glacier Collector: Received {0} messages.".format(str(len(messages))))
        # Iterate each message
        for message in messages:
            # Parse message (evaluate two levels to get to the body)
            msg_body = eval((eval(message.body)['Message']).replace('Decimal', 'int'))

            # message type is archive msgs
            if msg_body['type'] == 'archive':
                try:
                    jobid = msg_body['job_id']
                    etime = msg_body['complete_time']
                    username = msg_body['username']
                    filename = msg_body['s3_key_result_file']
                except KeyError as e:
                    message.delete()
                    continue

                newname = cnetid + '/' + username + '#' + filename[filename.find('/')+1:]

                # ensure file exists
                if not __check_exist__(result_bucket, filename):
                    continue

                # connect to RDS database to get job owner's role
                try:
                    conn = MySQLdb.connect(host=db_host, user=db_username, passwd=db_pwd, db=db_userdb, port=db_port)
                    dbcursor = conn.cursor()
                    dbcursor.execute(query, (username,))
                    user = dbcursor.fetchone()
                    dbcursor.close()
                    role = user[1]
                except Exception as e:
                    continue

                # double check user's role in case the user has upgraded before time limit
                if role != 'free_user':
                    message.delete()
                    continue

                # check time limit
                if int(time.time()) - etime > free_time_limit:
                    print("archive", newname)
                    if not __move_object__(result_bucket, filename, glacier_bucket, newname):
                        continue
                    message.delete()

            # message type is restore msgs
            elif msg_body['type'] == 'restore':
                try:
                    key = msg_body['key']
                except KeyError as e:
                    message.delete()
                    continue
                obj = s3.Object(glacier_bucket, key)

                # ensure file exists
                if not __check_exist__(glacier_bucket, key):
                    continue

                status = obj.restore
                print(key, obj.storage_class, status)

                # restore files haven't archived or have restored
                # http://boto3.readthedocs.io/en/latest/reference/services/s3.html#id26
                if obj.storage_class != 'GLACIER' or 'ongoing-request="false"' in status:
                    newname = cnetid + '/' + key[key.find('#')+1:]
                    print("restore", newname)
                    if not __move_object__(glacier_bucket, key, result_bucket, newname):
                        continue
                    message.delete()

    else:
        continue
