$(document).ready(function() {
	$('#date').datetimepicker();
	$('.deleteform').hide();
	$('.deletebutton').click(function(){
		$('.deletebutton').hide();
		$('.deleteform').show();
		})
 });
