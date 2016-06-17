%include('views/header.tpl')



<div class="container">

	<div class="page-header">
  	    <h2>User Profile</h2>
    </div>

    <div>
        <strong>Username:</strong> {{user.username}}<br/>
        <strong>Name:</strong> {{user.description}}<br/>
        <strong>Email:</strong> {{user.email_addr}}<br/>
        % level = str(user.role).split('_')[0]
        <strong>Subscription Level:</strong> {{level}}<br/>

        %if user.role == 'free_user':
        <br/>
        <div>
            <a href="{{get_url('subscribe')}}"><input class="btn btn-primary btn-lg" style="width:250px" type="submit" value="Upgrade to Premium"></a>
        </div>
        %end
    </div>


</div> <!-- container -->

%rebase('views/base', title='GAS - Annotation Request Received')