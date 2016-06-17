%include('views/header.tpl')

<script type="text/javascript">

// check the upload file info to insure it is valid
// https://developer.mozilla.org/en-US/docs/Using_files_from_web_applications
function checkinfo(btn){
    $('#upgrade').hide()
    $('#msg').hide()
    var file = document.getElementById('upload-file').files[0]
    btn.disabled = true;

    // check file ends with .vcf
    if( file != undefined && file.name.substring(file.name.length-4) == '.vcf') {
        var size = file.size;
        var name = file.name;
        console.log(name + ":" + size);

        // free user file size check
        if( '{{auth.current_user.role}}' == 'free_user') {
            if(size>{{size}}) {
                $('#upgrade').show()
                console.log("over");
                return false;
             }
        }
        btn.disabled = false;
        return true;
    }
    $('#msg').show()
    return false;
}
</script>

<div class="container">

	<div class="page-header">
		<h2>Annotate VCF File</h2>
	</div>

	<div class="form-wrapper">
    <form role="form" action="http://{{bucket_name}}.s3.amazonaws.com/" method="post" enctype="multipart/form-data">
			<input type="hidden" name="key" value="{{username}}/{{jobid}}~${filename}" />
			<input type="hidden" name="AWSAccessKeyId" value={{aws_key}} />
			<input type="hidden" name="acl" value="private" />
			<input type="hidden" name="success_action_redirect" value={{url}} />
			<input type="hidden" name="policy" value={{policy}} />
			<input type="hidden" name="signature" value={{signature}} />

      <div class="row">
        <div class="form-group col-md-5">
          <label for="upload">Select VCF Input File</label>
          <p id='msg' style="display:none; color:red;">Please select a VCF file!</p>
          <p id='upgrade' style="display:none; color:red;">File size exceeds free user limit! <a href="{{get_url('subscribe')}}">Upgrade now</a></p>
          <div class="input-group col-md-12">
            <span class="input-group-btn">
              <span class="btn btn-default btn-file btn-lg">Browse&hellip;
              <input class = "required" type="file" name="file" id="upload-file" /></span>
            </span>
            <input type="text" class="form-control" readonly />
          </div>
        </div>
      </div>

      <br />
			<div class="form-actions">
				<input id="submit-btn" onclick="return checkinfo(this)" class="btn btn-lg btn-primary" type="submit" value="Annotate" disabled/>
			</div>
    </form>
  </div>
  
</div> <!-- container -->

%rebase('views/base', title='GAS - Annotate')
