# Copyright (C) 2015 University of Chicago
#
import _mysql_exceptions

__author__ = 'Vas Vasiliadis <vas@uchicago.edu>'

import base64
import datetime
import hashlib
import hmac
import time
import uuid
import boto3
import botocore.session

from mpcs_utils import log, auth
from bottle import route, request, redirect, template, static_file, HTTPError, error

'''
*******************************************************************************
Set up static resource handler - DO NOT CHANGE THIS METHOD IN ANY WAY
*******************************************************************************
'''


@route('/static/<filename:path>', method='GET', name="static")
def serve_static(filename):
    # Tell Bottle where static files should be served from
    return static_file(filename, root=request.app.config['mpcs.env.static_root'])


'''
*******************************************************************************
check login info, avoid mysql connection lost and log the request
*******************************************************************************
'''


def __check_auth__(auth):
    MAX_TRIES = 100
    WAIT_TIME = 0.5
    tries = 0

    while True:
        # try to fetch users in MySql to ensure the connection in cork is not lost
        try:
            print len(auth._store.users)
        except Exception as e:
            # mysql connection lost, try again later
            time.sleep(WAIT_TIME)
            tries += 1
            if tries > MAX_TRIES:
                raise e
            print "try " + str(tries)
            continue
        else:
            break


def __check_request__(request):
    log.info(request.url)
    __check_auth__(auth)
    auth.require(fail_redirect='/login?redirect_url=' + request.url)


'''
*******************************************************************************
Home page
*******************************************************************************
'''


@route('/', method='GET', name="home")
def home_page():
    __check_auth__(auth)
    log.info(request.url)
    return template(request.app.config['mpcs.env.templates'] + 'home', auth=auth)


'''
*******************************************************************************
Registration form
*******************************************************************************
'''


@route('/register', method='GET', name="register")
def register():
    __check_auth__(auth)
    if (auth._beaker_session.get('username')) is not None:
        redirect('/annotations')
    log.info(request.url)
    return template(request.app.config['mpcs.env.templates'] + 'register',
                    auth=auth, name="", email="", username="", alert=False)


@route('/register', method='POST', name="register_submit")
def register_submit():
    __check_auth__(auth)
    auth.register(description=request.POST.get('name').strip(),
                  username=request.POST.get('username').strip(),
                  password=request.POST.get('password').strip(),
                  email_addr=request.POST.get('email_address').strip(),
                  role="free_user")
    return template(request.app.config['mpcs.env.templates'] + 'register',
                    auth=auth, alert=True)


@route('/register/<reg_code>', method='GET', name="register_confirm")
def register_confirm(reg_code):
    __check_auth__(auth)
    log.info(request.url)
    auth.validate_registration(reg_code)
    return template(request.app.config['mpcs.env.templates'] + 'register_confirm',
                    auth=auth)


'''
*******************************************************************************
Login, logout, and password reset forms
*******************************************************************************
'''


@route('/login', method='GET', name="login")
def login():
    __check_auth__(auth)
    log.info(request.url)
    redirect_url = "/annotations"
    # If the user is trying to access a protected URL, go there after auhtenticating
    if request.query.redirect_url.strip() != "":
        redirect_url = request.query.redirect_url

    return template(request.app.config['mpcs.env.templates'] + 'login',
                    auth=auth, redirect_url=redirect_url, alert=False)


@route('/login', method='POST', name="login_submit")
def login_submit():
    __check_auth__(auth)
    auth.login(request.POST.get('username'),
               request.POST.get('password'),
               success_redirect=request.POST.get('redirect_url'),
               fail_redirect='/login')


@route('/logout', method='GET', name="logout")
def logout():
    log.info(request.url)
    auth.logout(success_redirect='/login')


'''
*******************************************************************************
Core GAS code is below...
*******************************************************************************
'''

'''
*******************************************************************************
Subscription management handlers
*******************************************************************************
'''
import stripe


# Display form to get subscriber credit card info
@route('/subscribe', method='GET', name="subscribe")
def subscribe():
    __check_request__(request)
    if auth.current_user.role != request.app.config['mpcs.plans.free']:
        redirect('/profile')
    return template(request.app.config['mpcs.env.templates'] + "subscribe", user=auth.current_user)


# Process the subscription request
@route('/subscribe', method='POST', name="subscribe_submit")
def subscribe_submit():
    __check_request__(request)
    user = auth.current_user
    try:
        token = request.POST.get('stripe_token')
        cfg = request.app.config
        # need to set secret key here
        stripe.api_key = cfg['mpcs.stripe.secret_key']
        customer = stripe.Customer.create(
            card=token,
            plan="premium_plan",
            email=auth.current_user.email_addr,
            description=auth.current_user.username)
    except Exception as e:
        return HTTPError(503, str(e))

    # update role first
    user.update(role="premium_user")

    # restore
    # http://boto3.readthedocs.io/en/latest/reference/services/s3.html#id26
    archive_bucket = cfg['mpcs.aws.s3.archive_bucket']
    cnetid = cfg['mpcs.cnetid']
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(archive_bucket)

    for obj_sum in bucket.objects.filter(Prefix=cnetid + '/' + user.username + '#'):
        obj = s3.Object(obj_sum.bucket_name, obj_sum.key)
        if obj.storage_class == 'GLACIER' and obj.restore is None:
            resp = obj_sum.restore_object(
                RequestPayer='requester',
                RestoreRequest={'Days': 1000})
            print resp

        # publish a restore massage to glacier sns
        glacier_sns = cfg['mpcs.aws.sns.job_glacier_topic']
        sns = boto3.resource('sns')
        topic = sns.Topic(glacier_sns)
        data = {'type': 'restore', 'key': obj_sum.key}
        print data
        topic.publish(Message=str(data))

        return template(request.app.config['mpcs.env.templates'] + "subscribe_confirm", stripe_id=customer['id'])


'''
*******************************************************************************
Display the user's profile with subscription link for Free users
*******************************************************************************
'''


@route('/profile', method='GET', name="profile")
def user_profile():
    __check_request__(request)
    return template(request.app.config['mpcs.env.templates'] + "profile", user=auth.current_user)


'''
*******************************************************************************
Helper function to create policy and singnature
*******************************************************************************
'''


def __oauth__(input_bucket, redirect_url, limit):
    # http://docs.aws.amazon.com/AmazonS3/latest/dev/HTTPPOSTForms.html

    cred = botocore.session.Session().get_credentials()
    access_key = cred.access_key
    secret_key = cred.secret_key

    # http://stackoverflow.com/questions/15940280/how-to-get-utc-time-in-python
    exptime = datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    policy = '{"expiration":"%s",' \
             '"conditions":[{"acl":"private"},{"bucket":"%s"},' \
             '{"success_action_redirect": "%s"},' \
             '["starts-with","$key","zuomingli/"]' % (
                 exptime.strftime('%Y-%m-%dT%H:%M:%S.000Z'), input_bucket, redirect_url)
    if limit >= 0:
        policy += ',["content-length-range", 0, %s]]}' % limit
    else:
        policy += ']}'

    # https://docs.python.org/2/library/base64.html
    policy_b64 = base64.b64encode(policy.encode('utf-8'))

    # http://stackoverflow.com/questions/8338661/implementaion-hmac-sha1-in-python
    signature = base64.b64encode(hmac.new(secret_key.encode(), policy_b64, hashlib.sha1).digest())

    return {'awskey': access_key.encode(), 'policy': policy_b64, 'signature': signature}


'''
*******************************************************************************
Creates the necessary AWS S3 policy document and renders a form for
uploading an input file using the policy document
*******************************************************************************
'''


@route('/annotate', method='GET', name="annotate")
def upload_input_file():
    __check_request__(request)

    input_bucket = request.app.config['mpcs.aws.s3.inputs_bucket']
    size = request.app.config['mpcs.plans.free_file_size_limit']
    redirect_url = request.url[:request.url.rfind('/')] + "/annotate/job"
    cnetid = request.app.config['mpcs.cnetid']

    limit = -1
    if auth.current_user.role == 'free_user':
        limit = request.app.config['mpcs.plans.free_file_size_limit']
    oauth = __oauth__(input_bucket, redirect_url, limit)
    return template(request.app.config['mpcs.env.templates'] + "upload",
                    bucket_name=input_bucket, username=cnetid, jobid=str(uuid.uuid4()),
                    aws_key=oauth['awskey'], policy=oauth['policy'], signature=oauth['signature'],
                    url=redirect_url, auth=auth, size=size)


'''
*******************************************************************************
Accepts the S3 redirect GET request, parses it to extract 
required info, saves a job item to the database, and then
publishes a notification for the annotator service.
*******************************************************************************
'''


@route('/annotate/job', method='GET')
def create_annotation_job_request():
    __check_request__(request)

    cfg = request.app.config
    input_bucket = cfg['mpcs.aws.s3.inputs_bucket']
    result_bucket = cfg['mpcs.aws.s3.results_bucket']
    dynamodb_table = cfg['mpcs.aws.dynamodb.annotations_table']
    sns_arn = cfg['mpcs.aws.sns.job_request_topic']

    # check if the request is valid
    try:
        if request.query['etag'][0] != '"':
            raise Exception
    except:
        return HTTPError(403, body='You are requesting abnormally.')
    try:
        key = request.query['key']
        sp_key = key[key.find('/') + 1:]
        sp_jobname = sp_key[sp_key.find('~') + 1:]
        job_id = sp_key[:sp_key.find('~')]
        user = auth.current_user
    except:
        return HTTPError(404)

    # upload to dynamodb
    data = {'job_id': job_id,
            'username': user.username,
            'description': user.description,
            's3_inputs_bucket': input_bucket,
            's3_key_input_file': key,
            'input_file_name': sp_jobname,
            's3_results_bucket': result_bucket,
            'submit_time': int(time.time()),
            'status': 'PENDING',
            'notes': {},
            'documents': {}}
    print data
    ddb = boto3.resource('dynamodb')
    table = ddb.Table(dynamodb_table)
    table.put_item(Item=data)

    # publish a notification to request sns
    # http://boto3.readthedocs.io/en/latest/reference/services/sns.html
    sns = boto3.resource('sns')
    topic = sns.Topic(sns_arn)
    topic.publish(Message=str(data))
    return template(request.app.config['mpcs.env.templates'] + "upload_confirm", auth=auth, job_id=job_id)


'''
*******************************************************************************
List all annotations for the user
*******************************************************************************
'''


@route('/annotations', method='GET', name="annotations_list")
def get_annotations_list():
    __check_request__(request)

    cfg = request.app.config
    dynamodb_table = cfg['mpcs.aws.dynamodb.annotations_table']
    user = auth.current_user

    # query specific user's job
    ddb = boto3.resource('dynamodb')
    table = ddb.Table(dynamodb_table)
    res = table.query(IndexName='username-index',
                      KeyConditions={'username': {'AttributeValueList': [user.username], 'ComparisonOperator': 'EQ'}})
    jobs = res['Items']

    # sort jobs according to submit time
    jobs = sorted(jobs, key=lambda k: -k['submit_time'])

    return template(request.app.config['mpcs.env.templates'] + "list", auth=auth, jobs=jobs)


'''
*******************************************************************************
Helper function to get dynamodb table information of a job
*******************************************************************************
'''


def __get_detail__(jobid, request):
    cfg = request.app.config
    dynamodb_table = cfg['mpcs.aws.dynamodb.annotations_table']
    ddb = boto3.resource('dynamodb')
    table = ddb.Table(dynamodb_table)

    res = table.get_item(Key={'job_id': jobid})
    job = res['Item']
    return job


'''
*******************************************************************************
Display details of a specific annotation job and log file
*******************************************************************************
'''


@route('/annotations/<job_id>', method='GET', name="annotation_details")
def get_annotation_details(job_id):
    __check_request__(request)

    cfg = request.app.config
    result_bucket = cfg['mpcs.aws.s3.results_bucket']
    user = auth.current_user

    try:
        job = __get_detail__(job_id, request)
        # format time
        job['submit_time'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(job['submit_time']))
    except:
        return HTTPError(404, body='Job not found.')

    # check whether current user and the job's owner is matched
    if job['username'] != user.username:
        return HTTPError(403, body='Permission denied.')

    result_url = None
    log_content = None
    log_url = None
    if job['status'] == 'COMPLETED':
        etime = job['complete_time']
        job['complete_time'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(job['complete_time']))

        # generate log file download url
        # https://github.com/boto/boto3/issues/110
        client = boto3.client('s3')
        log_url = client.generate_presigned_url(
            'get_object', ExpiresIn=300,
            Params={'Bucket': result_bucket, 'Key': job['s3_key_log_file']})

        # read log file content
        s3 = boto3.resource('s3')
        log_obj = s3.Object(result_bucket, job['s3_key_log_file'])
        log_content = log_obj.get()['Body'].read()
        log_content = log_content.replace("\n", '<br/>')

        try:
            # check whether file is passed the time limit
            if int(time.time()) - etime <= eval(cfg['mpcs.plans.free_time_limit']) \
                    or user.role != cfg['mpcs.plans.free']:
                # check whether result file exists in result bucket
                # http://stackoverflow.com/questions/33842944/check-if-a-key-exists-in-a-bucket-in-s3-using-boto3
                res = s3.Object(result_bucket, job['s3_key_result_file']).load()
                # generate result file download url
                result_url = client.generate_presigned_url(
                    'get_object', ExpiresIn=300,
                    Params={'Bucket': result_bucket, 'Key': job['s3_key_result_file']})

        except Exception as e:
            print e

    return template(request.app.config['mpcs.env.templates'] + "detail", user=user, job=job,
                    result_url=result_url, log_url=log_url, content=log_content)


'''
*******************************************************************************
Error handler
ref: http://bottlepy.org/docs/dev/tutorial.html#error-pages
*******************************************************************************
'''


def __error_handler__(code, msg):
    return template(request.app.config['mpcs.env.templates'] + "error",
                    error=str(code), msg=msg)


@error(404)
def error404(error):
    return __error_handler__(404, "Something bad just happened.<br/>" + error.body)


@error(403)
def error403(error):
    return __error_handler__(403, "You are doing something bad.<br/>" + error.body)


@error(500)
def error500(error):
    msg = "Oops, please call me at 911"

    # send traceback email
    mailmsg = '<br/>' + error.body + "<br/>" + str(error.exception) + "<br/>" + str(
        error.traceback).replace('\n', '<br/>')
    mail_client = boto3.client('ses')
    sender = "zuomingli@ucmpcs.org"
    my_address = "lee.zuoming@gmail.com"
    res = mail_client.send_email(Source=sender, Destination={'ToAddresses': [my_address]},
                                 Message={'Subject': {'Data': 'Error Happened!'},
                                          'Body': {'Html': {'Data': mailmsg}}})
    return __error_handler__(500, msg)


@error(503)
def error503(error):
    return __error_handler__(503, "Something bad just happened.<br/>" + error.body)

### EOF
