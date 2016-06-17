import boto3
import sys
import subprocess
from bottle import run, post, request
from config import *

data_folder = "data/"
anntools_script = 'mpcs_anntools/run.py'


@post('/start')
def do_start():
    data = request.json
    s3 = boto3.resource('s3')

    key = data['s3_key_input_file']
    bucket = data['s3_inputs_bucket']
    jobid = data['job_id']
    sp_key = key.split('/')

    try:
        # download uploaded file
        # http://boto3.readthedocs.org/en/latest/reference/services/s3.html#bucket
        local_file = data_folder + sp_key[1]
        s3.Bucket(bucket).download_file(key, local_file)

        # spawn subprocess
        p = subprocess.Popen([sys.executable, anntools_script, local_file])
    except:
        status = "FAILED"
    else:
        status = "RUNNING"
    finally:
        # change status in dynamodb
        # http://boto3.readthedocs.org/en/latest/reference/services/dynamodb.html
        ddb = boto3.resource('dynamodb')
        table = ddb.Table(dynamodb_table)
        res = table.update_item(Key={'job_id': jobid}, AttributeUpdates={'status': {'Value': status, 'Action': 'PUT'}})
        if res['ResponseMetadata']['HTTPStatusCode'] != 200:
            raise Exception

    res = {'code': 200, 'data': {'job_id': str(jobid), 'input_file': sp_key[1]}}
    return res


run(host='0.0.0.0', port=8889, debug=True)
