function updatePath() {
    let match = $("#file").val().match(/\..*/);
    if (match && match[0].toLowerCase().indexOf(".tar") >= 0) {
        $("#language").attr("disabled", "");
    } else {
        $("#language").removeAttr("disabled");
    }

    if ($("#language").attr("disabled") == "disabled") {
        $("#path").val("/"+corpus+"/"+branch+"/uploads/"+$("#file").val().replace(/.*\\/, ""));
    } else if ($("#language").val() == "detect") {
        $("#path").val("/"+corpus+"/"+branch+"/uploads/"+$("#file").val().replace(/.*?\./, "")+"/"+$("#file").val().replace(/.*\\/, ""));
    } else {
        $("#path").val("/"+corpus+"/"+branch+"/uploads/"+$("#file").val().replace(/.*?\./, "")+"/"+$("#language").val()+"/"+$("#file").val().replace(/.*\\/, ""));
    }
}

$("#language").on("change", function() {
    updatePath();
});

$("#file").on("change", function() {
    updatePath();
});

let url = decodeURIComponent(window.location.search.substring(1)).split("&");

for (i=0; i<url.length; i++) {
    let urlParam = url[i].split("=");
        if (urlParam[0] == "corpus") {
    var corpus = urlParam[1];
        $("#back-link").attr("href", "/show_corpus/"+corpus);
        $("#back-link").text("Back to "+corpus);
    } else if (urlParam[0] == "branch") {
        var branch = urlParam[1];
    } else if (urlParam[0] == "language") {
        $("#language").val(urlParam[1]);
    } else if (urlParam[0] == "description") {
        $("#description").val(urlParam[1]);
    } else if (urlParam[0] == "direction" && urlParam[1] == "original") {
        $("#original")[0].outerHTML = '<input id="original" value="original" name="direction" type="radio" checked>';
    } else if (urlParam[0] == "direction" && urlParam[1] == "translation") {
        $("#translation")[0].outerHTML = '<input id="translation" value="translation" name="direction" type="radio" checked>';
    } else if (urlParam[0] == "autoimport" && urlParam[1] == "true") {
        $("#autoimport")[0].outerHTML = '<input id="autoimport" name="autoimport" type="checkbox" checked>';
    }
}

$("#uploadbutton").on("click", function() {
    $("#messages").append('<li id="uploadstatus">Uploading, please wait...</li>');
});

updatePath();
