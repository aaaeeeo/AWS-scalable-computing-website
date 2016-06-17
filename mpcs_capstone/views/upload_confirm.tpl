%include('views/header.tpl')

<div class="container">

	<div class="page-header">
  	<h2>Annotation Request Received</h2>
  </div>

	<p>Your annotation request was received and assigned ID 
 		<a href="/annotations/{{job_id}}">{{job_id}}</a>.</p>

</div> <!-- container -->

%rebase('views/base', title='GAS - Annotation Request Received')