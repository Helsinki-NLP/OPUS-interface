let baseurl = window.location.protocol + "//" + window.location.host

function update_branch() {
    $(document).off();
    $("#uploads").text("");
    $("#monolingual").text("");
    $("#parallel").text("");
    $("#branch").val($("#choose-branch").val());
    $.getJSON(baseurl+"/get_branch", {
	corpusname: $("#corpusname").text(),
	branch: $("#choose-branch").val()
    }, function(data) {
	subdir_to_list(data.uploads, "uploads");
	subdir_to_list(data.monolingual, "monolingual");
	subdir_to_list(data.parallel, "parallel");
	subdir_to_list(data.monolingual, "align-source-files");
	subdir_to_list(data.monolingual, "align-target-files");
    });
}

function formulate_datapath(datapath) {
    datapath = datapath.replace(/-_-/g, "/");
    datapath = datapath.replace(/-_DOT_-/g, ".");
    datapath = datapath.replace("monolingual", "xml");
    datapath = datapath.replace("parallel", "xml");
    return "/" + $("#corpusname").text() + "/" + $("#branch").val() + "/" + datapath;
}

var changedMetadata = {};
var mdvn = 0;

function showMetadata(datapath) {
    $("#importfile").css("display", "none");
    $("#importfile").text("import");
    $("#downloadfile").css("display", "none");
    $("#file-metadata").text("");
    $("#file-content").text("");
    $("#editmetadata").css("display", "none");
    let path = formulate_datapath(datapath);
    let inUploads = path.startsWith("/" + $("#corpusname").text() + "/" + $("#branch").val() + "/uploads/");
    $.getJSON(baseurl+"/get_metadata", {
	path: path
    }, function(data) {
	$("#editmetadata").css("display", "inline");
	$("#editmetadata").attr("edit", "false");
	for (i=0; i<data.metadataKeys.length; i++) {
	    let key = data.metadataKeys[i];
	    if (key == "owner" && data.metadata[key] == data.username && inUploads) {
		$("#importfile").css("display", "inline");
	    } else if (key == "status" && data.metadata[key] == "imported" && inUploads) {
		$("#importfile").text("import again");
	    } else if (!inUploads) {
		$("#downloadfile").css("display", "inline");
	    }
	    let metadataid = "metadatainputid"+mdvn
	    $("#file-metadata").append('<tr><td align="right" style="border: none; width: 1%; white-space: nowrap"><b>'+key+':</b></td><td style="border: none"><span class="metadatatext">'+data.metadata[key]+'</span><input id="'+metadataid+'" class="metadatainput" style="display: none" name="'+key+'" value="'+data.metadata[key]+'"></td></tr>');

	    $(document).on("change", "#"+metadataid, function() {
		changedMetadata[key] = $("#"+metadataid).val();
	    });
	    mdvn += 1;
	}
    });
}

var inputmn = 0;

function editMetadata(datapath) {
    let path = formulate_datapath(datapath);
    if ($("#editmetadata").attr("edit") == "false") {
	$("#editmetadata").attr("edit", "true");
	$(".metadatatext").css("display", "none");
	$(".metadatainput").css("display", "inline");
	$("#file-metadata").append('<tr id="addfieldrow"><td align="right" style="border: none; width: 1%"></td><td style="border: none;"><button id="addfieldbutton">add field</button></td></tr>');
	$("#addfieldbutton").off("click");
	$("#addfieldbutton").on("click", function() {
	    $('<tr><td style="border: none; width: 1%"><input id="addedfieldkey'+inputmn+'" class="metadatainput" style="text-align: right" placeholder="key"></td><td style="border: none;"><input id="addedfieldvalue'+inputmn+'" class="metadatainput" placeholder="value"></td></tr>').insertBefore("#addfieldrow");
	    inputmn += 1;
	});
	$("#file-metadata").append('<tr id="savemetadatarow"><td style="border: none; width: 1%"></td><td style="border: none;"><button id="savemetadatabutton">save changes</button></td></tr>');
	$("#savemetadatabutton").off("click");
	$("#savemetadatabutton").on("click", function() {
	    $(".metadatainput").attr("disabled", "");
	    $("#addfieldbutton").css("display", "none");
	    for (i=0; i<inputmn; i++) {
		let key = $("#addedfieldkey"+i).val();
		let value = $("#addedfieldvalue"+i).val();
		if (key != "" && value != "") {
		    changedMetadata[key] = value;
		}
	    }
	    inputmn = 0;
	    $.getJSON(baseurl+"/update_metadata", {
		changes: JSON.stringify(changedMetadata),
		path: path
	    }, function(data) {
		$("#messages")[0].innerHTML = "";
		$("#messages").append('<li>Updated metadata for file "' + path + '"</li>');
		showMetadata(datapath);
	    });
	});
    } else {
	$("#editmetadata").attr("edit", "false");
	$(".metadatatext").css("display", "inline");
	$(".metadatainput").css("display", "none");
	$("#savemetadatarow").remove();
	$("#addfieldrow").remove();
    }
}

function showFilecontent(datapath, windowid) {
    $(windowid).text("");
    let path = formulate_datapath(datapath);
    $.getJSON(baseurl+"/get_filecontent", {
	path: path
    }, function(data) {
	$(windowid).text(data.content);
    });
}

function importFile(datapath) {
    let path = formulate_datapath(datapath);
    $.getJSON(baseurl+"/import_file", {
	path: path
    }, function(data) {
	$("#messages")[0].innerHTML = "";
	$("#messages").append('<li>Started importing file "' + path + "'</li>");
    });
    update_branch();
    showOrHideTrees("monolingual", "parallel", "", "show");
}

function deleteFile(datapath, subdirname) {
    let path = formulate_datapath(datapath);
    if (confirm('Are you sure you want to delete "' + path + '"?')) {
	$.getJSON(baseurl+"/delete_file", {
	    path: path
	}, function(data) {
	    $("#messages")[0].innerHTML = "";
	    $("#messages").append('<li>File "' + path + "' deleted</li>");
	});
	update_branch();
	if (subdirname == "uploads") {
	    showOrHideTrees("monolingual", "parallel", "", "show");
	} else if (subdirname == "monolingual") {
	    showOrHideTrees("uploads", "parallel", "", "show");
	} else if (subdirname == "parallel") {
	    showOrHideTrees("uploads", "monolingual", "", "show");
	}
    }
}

function downloadFile(datapath, filename) {
    let path = formulate_datapath(datapath);
    window.location.href = baseurl+"/download_file?path="+path+"&filename="+filename;
    /*
    console.log(path, filename);
    $.getJSON(baseurl+"/download_file", {
	path: path,
	filename: filename
    }, function(data) {
	console.log(data);
    });
    */
}

function subdir_to_list(directories, id_name){
    for (let i=0; i<directories.length; i++) {
	let subdir = id_name+"-_-"+directories[i][0];
	subdir = subdir.replace(/\./g, "-_DOT_-");	
	$("#"+id_name).append('<li id="'+subdir+'" ptype="' + directories[i][1] + '" opened="none"><span style="cursor: pointer">'+directories[i][0]+'</span></li>');
	let ptype = directories[i][1];
	if (ptype == "dir") {
	    $("#"+subdir).on("click", function() {
		open_or_close(subdir);
	    });
	} else if (ptype == "file"){
	    processFile(directories[i][0], subdir, id_name);
	}
    }
}

$("#searchcorpus").on("keyup", function() {
    if ($("#searchcorpus").val() != "") {
	$.getJSON(baseurl+"/search", {
	    corpusname: $("#searchcorpus").val()
	}, function(data) {
	    $("#searchresult")[0].innerHTML = "";
	    for (let i=0; i<data.result.length; i++) {
		$("#searchresult").append('<li><a href="/show_corpus/'+data.result[i]+'">'+data.result[i]+'</a></li>');
	    }
	});
    } else {
	$("#searchresult")[0].innerHTML = "";
    }
});

$("#clonebranch").on("click", function() {
    let corpusname = $("#corpusname").text();
    let branchclone = $("#choose-branch").val();
    let username = $("#username").text();
    window.location.href = baseurl+"/clone_branch?branch="+username+"&corpusname="+corpusname+"&branchclone="+branchclone;
    /*
    $.getJSON(baseurl+"/clone_branch", {
	path: path
    }, function(data) {
	console.log(data);
    });
    */
});

function open_subdir(subdir) {
    $.getJSON(baseurl+"/get_subdirs", {
	corpusname: $("#corpusname").text(),
	branch: $("#choose-branch").val(),
	subdir: "/"+subdir
    }, function(data) {
	let subdirs = data.subdirs;
	let subdir_list = '<li id="'+subdir+'_list"><ul id="'+subdir+'_list2" style="padding-left: 20px; list-style-type: none">'
	for (let i=0; i<subdirs.length; i++) {
	    let subdir_id = subdir+"-_-"+subdirs[i][0]
	    subdir_id = subdir_id.replace(/\./g, "-_DOT_-");
	    let ptype = subdirs[i][1];
	    if (ptype == "dir") {
		subdir_list += '<li id="'+subdir_id+'" ptype="'+subdirs[i][1]+'" opened="none"><span style="cursor: pointer">'+subdirs[i][0]+'</span></li>';
		$(document).on("click", "#"+subdir_id, function() {
		    open_or_close(subdir_id);
		});
	    } else if (ptype == "file") {
		if (subdir.match("^align")) {
		    subdir_list += '<li id="'+subdir_id+'" ptype="'+subdirs[i][1]+'" opened="none"><button id="'+subdir_id+'-align">+</button><span id="'+subdir_id+'-file" style="cursor: pointer">'+subdirs[i][0]+'</span></li>';
		    processAlignment(subdirs[i][0], subdir_id, subdir);
		} else {
		    subdir_list += '<li id="'+subdir_id+'" ptype="'+subdirs[i][1]+'" opened="none"><span style="cursor: pointer">'+subdirs[i][0]+'</span></li>';
		    processFile(subdirs[i][0], subdir_id, subdir);
		}
	    }
	}
	
	if (subdirs.length == 0) {
	    subdir_list += "<li>---</li>";
	}
	
	subdir_list += "</ul></li>";

	$("#"+subdir).after(subdir_list);
    });
}

var sourcenum = 0;
var targetnum = 0;
var linenumber = 0;

function processAlignment(filename, subdir_id, subdir) {
    $(document).on("click", "#"+subdir_id+"-file", function() {
	if (subdir.match("^align-source-files")) {
	    $("#align-source-file-structure").css("display", "none");
	    $("#align-source-file-content-view").css("display", "");
	    showFilecontent(subdir_id.replace(/align-source-files/, "xml"), "#align-source-file-content");
	} else if (subdir.match("^align-target-files")) {
	    $("#align-target-file-structure").css("display", "none");
	    $("#align-target-file-content-view").css("display", "");
	    showFilecontent(subdir_id.replace(/align-target-files/, "xml"), "#align-target-file-content");
	}
    });
    $(document).on("click", "#"+subdir_id+"-align", function() {
	let name = subdir.replace(/-_-/g, "/").replace(/^.*?\//, "")+"/"+filename;
	let soutar = "";
	let num = -1;
	if (subdir.match("^align-source-files")) {
	    sourcenum += 1;
	    num = sourcenum;
	    soutar = "source";
	} else if (subdir.match("^align-target-files")) {
	    targetnum += 1;
	    num = targetnum;
	    soutar = "target";
	}
	if (Math.max(sourcenum, targetnum) > linenumber) {
	    create_alignment_row()
	}
	$("#"+soutar+"-align-cell"+num).text(name);
	let sourcefile = $("#source-align-cell"+linenumber).text();
	let targetfile = $("#target-align-cell"+linenumber).text();
	if (sourcefile != "" && targetfile != "") {
	    $.getJSON(baseurl+"/add_alignment_candidate", {
		filename: $("#corpusname").text()+"/"+$("#choose-branch").val()+"/xml/"+sourcefile,
		add_candidate: "xml/"+targetfile
	    }, function(data) {
		console.log(data)
	    });
	}
    });
}

function create_alignment_row() {
    linenumber += 1;
    $("#selected-align-files").append('<tr id="selected-align'+linenumber+'"> \
<td id="delete-align-cell'+linenumber+'" style="width: 5%; border: none"><button id="delete-align-row-button'+linenumber+'">-</button></td> \
<td id="source-align-cell'+linenumber+'" style="width: 47%; border: none"></td> \
<td id="target-align-cell'+linenumber+'" style="width: 33%; border: none"></td> \
<td id="align-button-cell'+linenumber+'" style="width: 15%; border: none"><input id="selected-align-row'+linenumber+'" type="checkbox"><button id="align-button'+linenumber+'">align</button></td> \
</tr>');
    let currentid = linenumber;
    if ($("#align-all-selected").css("display") == "none") {
	$("#align-all-selected").css("display", "");
    }
    $(document).on("click", "#delete-align-row-button"+linenumber, function() {
	delete_alignment_row(currentid);
    });
    $(document).on("click", "#align-button"+linenumber, function() {
	let sourcefile = $("#corpusname").text()+"/"+$("#choose-branch").val()+"/xml/"+$("#source-align-cell"+currentid).text();
	let files = {};
	files[sourcefile] = "xml/"+$("#target-align-cell"+currentid).text();
	align_candidates(files, [currentid]);
    });
}

function align_candidates(files, deleteids) {
    $("#messages")[0].innerHTML = "";
    $("#messages").append('<li>Started aligning files...</li>');
    $.getJSON(baseurl+"/align_candidates", {
	files: JSON.stringify(files)
    }, function(data) {
	console.log(data)
	for (let i=0; i<deleteids.length; i++) {
	    $("#selected-align"+deleteids[i]).remove();
	}
	if ($("#selected-align-files")[0].childElementCount == 0) {
	    $("#align-all-selected").css("display", "none");
	}
    });
}

$("#align-all-selected-button").on("click", function() {
    let files = {};
    let deleteids = []
    for (let i=1; i<=linenumber; i++) {
	if ($("#selected-align-row"+i).prop("checked") == true) {
	    let sourcefile = $("#corpusname").text()+"/"+$("#choose-branch").val()+"/xml/"+$("#source-align-cell"+i).text();
	    files[sourcefile] = "xml/"+$("#target-align-cell"+i).text();
	    deleteids.push(i);
	}
    }
    if (files != "") {
	align_candidates(files, deleteids);
    }
});

$("#select-all-checkboxes").on("click", function() {
    if ($("#select-all-checkboxes").prop("checked") == true) {
	for (let i=1; i<=linenumber; i++) {
	    $("#selected-align-row"+i).prop("checked", true);
	}
    } else if ($("#select-all-checkboxes").prop("checked") == false) {
	for (let i=1; i<=linenumber; i++) {
	    $("#selected-align-row"+i).prop("checked", false);
	}
    }
});

function delete_alignment_row(deleteid) {
    let sourcefile = $("#source-align-cell"+deleteid).text();
    let targetfile = $("#target-align-cell"+deleteid).text();
    $.getJSON(baseurl+"/remove_alignment_candidate", {
	filename: $("#corpusname").text()+"/"+$("#choose-branch").val()+"/xml/"+sourcefile,
	rm_candidate: "xml/"+targetfile
    }, function(data) {
	console.log(data)
	if (sourcefile == "") {
	    sourcenum += 1;
	}
	if (targetfile == "") {
	    targetnum += 1;
	}
	$("#selected-align"+deleteid).remove();
	if ($("#selected-align-files")[0].childElementCount == 0) {
	    $("#align-all-selected").css("display", "none");
	}
    });
}

function list_alignment_candidates() {
    $("#selected-align-files")[0].innerHTML = "";
    $("#align-all-selected").css("display", "none");
    $("#select-all-checkboxes").prop("checked", false);
    $.getJSON(baseurl+"/list_alignment_candidates", {
	corpus: $("#corpusname").text(),
	branch: $("#choose-branch").val()
    }, function(data) {
	for (let i=0; i<data.file_list.length; i++) {
	    let source_file = data.file_list[i];
	    let candidates = data.candidates[source_file];
	    for (let j=0; j<candidates.length; j++) {
		let target_file = candidates[j];
		create_alignment_row();
		sourcenum++;
		targetnum++;
		$("#source-align-cell"+sourcenum).text(source_file);
		$("#target-align-cell"+targetnum).text(target_file);
	    }
	}
    });
};

$("#find-align-candidates").on("click", function() {
    $("#messages")[0].innerHTML = "";
    $("#messages").append('<li>Started finding alignment candidates...</li>');
    $.getJSON(baseurl+"/find_alignment_candidates", {
	corpus: $("#corpusname").text(),
	branch: $("#choose-branch").val()
    }, function(data) {
	console.log(data);
	list_alignment_candidates();
    });
});
    
function processFile(filename, path, root) {
    $(document).on("click", "#"+path, function() {
	$("#editalignment").css("display", "none");
	$("#filename").text(filename);
	showMetadata(path);
	$("#viewfile").text("view");
	$("#viewfile").attr("showing", "metadata");
	let subdirname = root.replace(/-_-.*/, "");
	if (subdirname == "uploads") {
	    showOrHideTrees("monolingual", "parallel", "uploads", "hide");
	    $("#importfile").off("click");
	    $("#importfile").on("click", function() {
		importFile(path);
	    });
	} else if (subdirname == "monolingual") {
	    showOrHideTrees("uploads", "parallel", "monolingual", "hide");
	} else if (subdirname == "parallel") {
	    showOrHideTrees("uploads", "monolingual", "parallel", "hide");
	    $("#editalignment").css("display", "inline");
	}
	$("#viewfile").off("click");
	$("#viewfile").on("click", function() {
	    switchMetadataAndContent(path);
	});
	$("#deletefile").off("click");
	$("#deletefile").on("click", function() {
	    deleteFile(path, subdirname);
	});
	$("#downloadfile").off("click");
	$("#downloadfile").on("click", function() {
	    downloadFile(path, filename);
	});
	$("#editmetadata").off("click");
	$("#editmetadata").on("click", function() {
	    editMetadata(path);
	});
	$("#editalignment").off("click");
	$("#editalignment").on("click", function() {
	    editAlignment(path);
	});
    });
}

function editAlignment(path) {
    $.getJSON(baseurl+"/edit_alignment", {
	path: formulate_datapath(path)
    }, function(data) {
	$("#messages")[0].innerHTML = "";
	$("#messages").append('<li>Preparing Interactive Sentence Alignment...</li>');
	setTimeout(function () {
	    window.location.href = "http://vm1637.kaj.pouta.csc.fi/html/isa/"+data.username+"/"+$("#corpusname").text()+"/index.php";
	}, 2000);
    });
}

function switchMetadataAndContent(subdir_id) {
    if ($("#viewfile").attr("showing") == "metadata") {
	$("#file-metadata").text("");
	$("#editmetadata").css("display", "none");
	showFilecontent(subdir_id, "#file-content");
	$("#viewfile").text("metadata");
	$("#viewfile").attr("showing", "content");
    } else if ($("#viewfile").attr("showing") == "content") {
	showMetadata(subdir_id);
	$("#viewfile").text("view");
	$("#viewfile").attr("showing", "metadata");
    }
}

function showOrHideTrees(tree1, tree2, remain, status) {
    if (status == "hide") {
	var displayfile = "";
	var displaytree = "none";
	$("#filedisplay-header-cell").attr("tree", remain);
    } else if (status == "show") {
	var displayfile = "none";
	var displaytree = "";
    }
    $(".filedisplay-cell").css("display", displayfile);
    $("#"+tree1+"-column").css("display", displaytree);
    $("."+tree1+"-cell").css("display", displaytree);
    $("#"+tree2+"-column").css("display", displaytree);
    $("."+tree2+"-cell").css("display", displaytree);
}

function open_or_close(subdir) {
    if ($("#"+subdir).attr("opened") == "none") {
	open_subdir(subdir);
	$("#"+subdir).attr("opened", "true");
    } else if ($("#"+subdir).attr("opened") == "true") {
	$("#"+subdir+"_list").css("display", "none");
	$("#"+subdir).attr("opened", "false");
	/*
	$("#"+subdir+"_list2").children().each(function( index ) {
	    $(document).off("click", "#"+$(this).attr("id"));
	});
	$("#"+subdir+"_list").remove();
	$("#"+subdir).attr("opened", "none");
	*/
    } else if ($("#"+subdir).attr("opened") == "false") {
	$("#"+subdir+"_list").css("display", "block");
	$("#"+subdir).attr("opened", "true");
    }
}

$("#choose-branch").on("change", function() {
    update_branch();
});

$("#filedisplay-close").on("click", function() {
    let tree = $("#filedisplay-header-cell").attr("tree");
    if (tree == "uploads") {
	showOrHideTrees("monolingual", "parallel", "", "show");
    } else if (tree == "monolingual") {
	showOrHideTrees("parallel", "uploads", "", "show");
    } else if (tree == "parallel") {
	showOrHideTrees("uploads", "monolingual", "", "show");
    }
});

$("#close-align-source-file-content").on("click", function() {
    $("#align-source-file-structure").css("display", "");
    $("#align-source-file-content-view").css("display", "none");
});

$("#close-align-target-file-content").on("click", function() {
    $("#align-target-file-structure").css("display", "");
    $("#align-target-file-content-view").css("display", "none");
});

$("#align-button").on("click", function() {
    $("#file-structure-table").css("display", "none");
    $("#align-selection-table").css("display", "");
    list_alignment_candidates();
});

$("#close-alignment").on("click", function() {
    $("#align-selection-table").css("display", "none");
    $("#file-structure-table").css("display", "");
});

function delete_item(tobedeleted, itemtype){
    if (confirm('Are you sure you want to delete ' + itemtype +' "' + tobedeleted + '"?')) {
	$.getJSON(baseurl+"/remove_"+itemtype, {
	    tobedeleted: tobedeleted
	}, function(data) {
	    console.log(data);
	    $("#"+itemtype+"-li-"+tobedeleted).remove();
	    $("#messages")[0].innerHTML = "";
	    $("#messages").append('<li>Deleted ' + itemtype +' "' + tobedeleted + '"</li>');
	});
    }
}

$(".remove-item-button").on("click", function() {
    let corpusname = $(this).attr("corpusname");
    let groupname = $(this).attr("groupname");
    if (corpusname) {
        delete_item(corpusname, "corpus");
    } else if (groupname) {
        delete_item(groupname, "group");
    }
});

$("#settings").on("click", function() {
    window.location.href = baseurl+"/corpus_settings/" + $("#corpusname").text();
});

let branchname = decodeURIComponent(window.location.search.substring(1)).split("&")[0].split("=")[1];

if (branchname != undefined) {
    $("#choose-branch").val(branchname);
}

update_branch();
