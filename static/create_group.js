let usernumber = 0

function adduser(tobeadded) {
    if ($("#userlist")[0].childElementCount > 0) {
	$("#selected-users").append('<li id="user' + usernumber + '"><button id="remove-user' + usernumber + '" type="button" style="padding: 0px">x</button>' + tobeadded + '</li>');
	$("#members").val($("#members").val()+tobeadded+",");
	let userid = "#user" + usernumber;
	$("#select-option-user-"+tobeadded).remove();
	$(document).on("click", "#remove-user"+usernumber, function() {
	    let username = $(userid).text().substring(1, $(userid).text().length);
	    $("#members").val($("#members").val().replace(username+",", ""));
	    $(userid).remove();
	    $("#userlist").append('<option id="select-option-user-' + tobeadded + '">' + tobeadded + '</option');
	});
	usernumber++;
    }
}
    
$("#adduser").on("click", function() {
    adduser($("#userlist").val());
});
