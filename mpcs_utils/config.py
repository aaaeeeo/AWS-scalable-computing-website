domain = "zuomingli.ucmpcs.org"

input_bucket = "gas-inputs"
result_bucket = "gas-results"
glacier_bucket = "gas-archive"
cnetid = "zuomingli"
result_suffix = '.annot.vcf'
log_suffix = '.vcf.count.log'
dynamodb_table = "zuomingli_annotations"
request_sqs = "zuomingli_job_requests"
request_sns = "arn:aws:sns:us-east-1:127134666975:zuomingli_job_notifications"
result_sns = "arn:aws:sns:us-east-1:127134666975:zuomingli_results_notifications"
result_sqs = "zuomingli_results_queue"
glacier_sns = "arn:aws:sns:us-east-1:127134666975:zuomingli_glacier_collect"
glacier_sqs = "zuomingli_glacier_queue"

db_host = "zuomingli-auth-db.catcuq1wrjmn.us-east-1.rds.amazonaws.com"
db_port = 3306
db_username = "zuomingli"
db_pwd = "shaolin7684"
db_userdb = "gasauth"

free_time_limit = 7200
tplname = "notification_email.tpl"
