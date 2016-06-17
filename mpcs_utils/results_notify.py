from __future__ import print_function

import boto3
import MySQLdb
from config import *

sender = cnetid + "@ucmpcs.org"
query = "SELECT * FROM users WHERE username=%s"

sqs = boto3.resource('sqs')
s3 = boto3.resource('s3')
queue = sqs.get_queue_by_name(QueueName=result_sqs)
mail_client = boto3.client('ses')


# get a single job detail from dynamodb
def __get_detail__(jobid):
    ddb = boto3.resource('dynamodb')
    table = ddb.Table(dynamodb_table)

    res = table.get_item(Key={'job_id': jobid})
    job = res['Item']
    return job


while True:
    # print("Asking SQS for up to 10 messages...")
    # Get messages
    messages = queue.receive_messages(MaxNumberOfMessages=10, WaitTimeSeconds=20)

    # If a message was read, extract job parameters from the message body
    if len(messages) > 0:
        print("Results notify: Received {0} messages.".format(str(len(messages))))
        # Iterate each message
        for message in messages:
            # Parse message (evaluate two levels to get to the body)
            msg_body = eval(eval(message.body)['Message'])
            try:
                jobid = msg_body['job_id']
                job = __get_detail__(jobid)
                username = job['username']
                filename = job['input_file_name']
            except KeyError as e:
                message.delete()
                continue

            # connect to RDS database to get job owner's email and role
            try:
                conn = MySQLdb.connect(host=db_host, user=db_username, passwd=db_pwd, db=db_userdb, port=db_port)
                dbcursor = conn.cursor()
                dbcursor.execute(query, (username,))
                user = dbcursor.fetchone()
                dbcursor.close()
                email = user[3]
                role = user[1]
            except Exception as e:
                continue

            # send email using template string
            tpl = open(tplname).read()
            res = mail_client.send_email(Source=sender, Destination={'ToAddresses': [email]},
                                         Message={'Subject': {'Data': 'One of your GAS annotation job completed!'},
                                                  'Body': {'Html': {
                                                      'Data': tpl % {'username': username, 'file': filename,
                                                                     'job_id': jobid, 'domain': domain}}}})
            print("notify", jobid, email)

            # publish a achieve message to glacier sns if it is a free user
            if role == 'free_user':
                data = job
                data['type'] = 'archive'
                sns = boto3.resource('sns')
                topic = sns.Topic(glacier_sns)
                print("publish archive", data)
                topic.publish(Message=str(data))

            message.delete()

    else:
        continue
