if ($("#flash-msgs")[0].innerHTML.trim() != "" || $("#messages")[0].innerHTML.trim() != "") {
    $("#message-div").css("display", "block");
}

$("#clear-messages").on("click", function() {
    $("#flash-msgs")[0].innerHTML = "";
    $("#messages")[0].innerHTML = "";
    $("#message-div").css("display", "none");
});
