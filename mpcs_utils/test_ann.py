import boto3
import time

count = 0
while True:
    time.sleep(0.5)
    data = {'job_id': "59e8e76b-956b-4968-ad7f-5008863bbd5b",
            'username': "test",
            'description': "test",
            's3_inputs_bucket': "gas-inputs",
            's3_key_input_file': "zuomingli/59e8e76b-956b-4968-ad7f-5008863bbd5b~free_1.vcf",
            'input_file_name': "free_1.vcf",
            's3_results_bucket': "gas-results",
            'submit_time': int(time.time()),
            'status': 'PENDING',
            'notes': {},
            'documents': {}}
    count += 1
    print count

    # publish a notification to request sns
    # http://boto3.readthedocs.io/en/latest/reference/services/sns.html
    sns = boto3.resource('sns')
    topic = sns.Topic("arn:aws:sns:us-east-1:127134666975:zuomingli_job_notifications")
    topic.publish(Message=str(data))
