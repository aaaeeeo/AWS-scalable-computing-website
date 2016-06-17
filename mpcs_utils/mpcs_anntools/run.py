import os
import sys
import time

import boto3
import driver

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir))
from config import *


# A rudimentary timer for coarse-grained profiling
class Timer(object):
    def __init__(self, verbose=False):
        self.verbose = verbose

    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, *args):
        self.end = time.time()
        self.secs = self.end - self.start
        self.msecs = self.secs * 1000  # millisecs
        if self.verbose:
            print("Elapsed time: %f ms" % self.msecs)


# using requests library to post to S3 to upload result files
# http://docs.python-requests.org/en/master/
def __upload__():
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(result_bucket)

    # upload result file
    bucket.upload_file(data_folder + result_filename, cnetid + result_filename)

    # upload log file
    bucket.upload_file(data_folder + log_filename, cnetid + log_filename)


# change status in dynamodb
# http://boto3.readthedocs.org/en/latest/reference/services/dynamodb.html
def __report_status__(jobid, status):
    ddb = boto3.resource('dynamodb')
    table = ddb.Table(dynamodb_table)
    if status == "COMPLETED":
        res = table.update_item(
            Key={'job_id': jobid},
            AttributeUpdates={'status': {'Value': status, 'Action': 'PUT'},
                              's3_key_result_file': {'Value': cnetid + result_filename,
                                                     'Action': 'PUT'},
                              's3_key_log_file': {'Value': cnetid + log_filename, 'Action': 'PUT'},
                              'complete_time': {'Value': complete_time, 'Action': 'PUT'}})
    else:
        res = table.update_item(Key={'job_id': jobid},
                                AttributeUpdates={'status': {'Value': status, 'Action': 'PUT'}})
    if res['ResponseMetadata']['HTTPStatusCode'] != 200:
        raise Exception


# publish job to result SNS
def __publish__(jobid):
    data = {'job_id': jobid, 'complete_time': complete_time}
    sns = boto3.resource('sns')
    topic = sns.Topic(result_sns)
    topic.publish(Message=str(data))


if __name__ == '__main__':
    try:
        # resolve file names
        input_file_name = sys.argv[1]
        data_folder = input_file_name[:input_file_name.find('/')]
        file_name = input_file_name[input_file_name.find('/'):input_file_name.rfind('.')]
        jobid = input_file_name[input_file_name.find('/') + 1:input_file_name.find('~')]
        result_filename = file_name + result_suffix
        log_filename = file_name + log_suffix

        # run
        if input_file_name[input_file_name.rfind('.'):] != '.vcf':
            raise Exception
        with Timer() as t:
            driver.run(input_file_name, 'vcf')
        print("Total runtime: %s seconds" % t.secs)

        # upload to S3
        __upload__()

        complete_time = int(time.time())

        # publish job to result SNS
        __publish__(jobid)

    except Exception as e:
        print(e)
        # report failure
        __report_status__(jobid, 'FAILED')
    else:
        # report success
        __report_status__(jobid, 'COMPLETED')
    finally:
        # clean up
        os.remove(input_file_name)
        os.remove(data_folder + result_filename)
        os.remove(data_folder + log_filename)
        pass
