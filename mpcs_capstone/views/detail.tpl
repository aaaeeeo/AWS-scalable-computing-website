%include('views/header.tpl')


<script>
// show and hide log file content
function dis(){
        if($('#text').is(":hidden")) {
            $('#label').html("hide");
        }
        else {
            $('#label').html("view");
        }
        $('#text').toggle();
};
</script>


<div class="container">

	<div class="page-header">
  	    <h2>Annotation Job Detail</h2>
    </div>

    <div>
        <strong>Job ID:</strong> {{job['job_id']}}<br/>
        <strong>Input File:</strong> {{job['input_file_name']}}<br/>
        <strong>Submit Time:</strong> {{job['submit_time']}}<br/>

        % # set row color according to status
        % color = 'orange'
        % color = 'red' if job['status']=="FAILED" else color
        % color = 'green' if job['status']=="COMPLETED" else color

        <strong>Status:</strong> <my style="color:{{color}};">{{job['status']}}</my><br/>
    </div>

    %if job['status'] == "COMPLETED":
        <strong>Complete Time:</strong> {{job['complete_time']}}<br/>
    <hr />
    <div>

        % # check if result file is available
        % if result_url is not None:
        <strong>Result:</strong> <a href="{{result_url}}">download</a><br/>
        % elif user.role == 'free_user':
        <strong>Result:</strong> <a href="{{get_url('subscribe')}}">upgrade to Premium for download</a><br/>
        % else:
        <strong>Result:</strong> Oops, unavailable now, please check later or call me at 911<br/>
        % end

        <strong>Log:</strong> <a onclick="dis()" id="label">view</a> <a href="{{log_url}}">download</a><br/><br/>
        <div id="text" style="display:none; color:green;">
        <my>{{!content}}</my>
        </div>
    </div>
    %end
    <hr />
    <a href="{{get_url("annotations_list")}}">Back to list</a>

</div> <!-- container -->

%rebase('views/base', title='GAS - Annotation Request Received')