from __future__ import print_function
import boto3
import sys
import subprocess
from config import *

data_folder = "data/"
anntools_script = 'mpcs_anntools/run.py'

sqs = boto3.resource('sqs')
s3 = boto3.resource('s3')
queue = sqs.get_queue_by_name(QueueName=request_sqs)

while True:
    # print("Asking SQS for up to 10 messages...")
    # Get messages
    messages = queue.receive_messages(MaxNumberOfMessages=10, WaitTimeSeconds=20)

    # If a message was read, extract job parameters from the message body

    if len(messages) > 0:
        print("Jobs runner: Received {0} messages.".format(str(len(messages))))
        # Iterate each message
        for message in messages:
            # Parse message (evaluate two levels to get to the body)
            msg_body = eval(eval(message.body)['Message'])
            try:
                key = msg_body['s3_key_input_file']
                bucket = msg_body['s3_inputs_bucket']
                jobid = msg_body['job_id']
                sp_key = key[key.find('/') + 1:]
            except KeyError as e:
                message.delete()
                continue

            try:
                # download uploaded file
                # http://boto3.readthedocs.org/en/latest/reference/services/s3.html#bucket
                local_file = data_folder + sp_key
                s3.Bucket(bucket).download_file(key, local_file)

                # spawn subprocess
                p = subprocess.Popen([sys.executable, anntools_script, local_file])
            except Exception as e:
                print(e)
                status = "FAILED"
            else:
                status = "RUNNING"
                message.delete()
            finally:
                # change status in dynamodb
                # http://boto3.readthedocs.org/en/latest/reference/services/dynamodb.html
                ddb = boto3.resource('dynamodb')
                table = ddb.Table(dynamodb_table)
                res = table.update_item(Key={'job_id': jobid},
                                        AttributeUpdates={'status': {'Value': status, 'Action': 'PUT'}})
                if res['ResponseMetadata']['HTTPStatusCode'] != 200:
                    raise Exception
    else:
        continue
