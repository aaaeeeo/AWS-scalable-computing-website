%include('views/header.tpl')
%import time


<div class="container">

	<div class="page-header">
  	    <h2>Annotation Jobs</h2>
    </div>
    <div>
        <a href="{{get_url('annotate')}}"><input class="btn btn-primary btn-lg" style="width:250px" type="submit" value="Upload new job"></a>
    </div>
    <br/>
    %if len(jobs)<=0:
    <h3>You have no job, <a href="{{get_url('annotate')}}">upload</a> now!</h3>
    %else:
    <table class="table table-striped table-hover">
        <th>Job ID</th>
        <th>Filename</th>
        <th>Submit Time</th>
        <th>Status</th>
        %for obj in jobs:

        % # format time
        % obj['submit_time'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(obj['submit_time']))

        % # set row color according to status
        % lab = 'warning'
        % lab = 'danger' if obj['status']=="FAILED" else lab
        % lab = 'success' if obj['status']=="COMPLETED" else lab
        % color = 'orange'
        % color = 'red' if obj['status']=="FAILED" else color
        % color = 'green' if obj['status']=="COMPLETED" else color

            <tr class="{{lab}}">
                <td><a href="annotations/{{obj['job_id']}}">{{obj['job_id']}}</a></td>
                <td><strong>{{obj['input_file_name']}}</strong></td>
                <td>{{obj['submit_time']}}</td>
                <td style="color:{{color}}">{{obj['status']}}</td>
            </tr>
        %end
        %end
     </table>

</div> <!-- container -->

%rebase('views/base', title='GAS - Annotation Request Received')