%include('views/header.tpl')


<div class="container">

	<div class="page-header">
  	    <h2>{{error}}</h2>
    </div>

    <div>
        <strong style="color:red">{{!msg}}</strong><br/>
     </div>
    <br/>
     <div>
        <a href="/">Back to home</a>
     </div>



</div> <!-- container -->

%rebase('views/base', title='GAS - Annotation Request Received')