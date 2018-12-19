from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, send_file, send_from_directory
from wtforms import Form, BooleanField, StringField, PasswordField, validators
from passlib.hash import sha256_crypt
from pymysql import escape_string as thwart
import gc
from dbconnect import connection
from functools import wraps
import sqlite3
from sqlalchemy import create_engine
import pickle
import os
from werkzeug.utils import secure_filename
import time
import xml_parser
import re
from urllib.parse import urlparse, urljoin
import request_handler
import json
import html

rh = request_handler.RequestHandler()

app = Flask(__name__)

UPLOAD_FOLDER = "/home/cloud-user/uploads"
download_folder= "/home/cloud-user/downloads"
ALLOWED_EXTENSIONS = set(['pdf', 'doc', 'txt', 'xml', 'html', 'tar', 'gz', 'epub'])

with open(app.root_path+"/iso639-1.dat", "rb") as f:
    iso639_1 = pickle.load(f)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

key = os.environ["SECRETKEY"]
app.secret_key = key

previous_download = ""

corpus_creation_options = {
    "pdf_reader_options": ["tika", "standard", "raw", "layout", "combined"],
    "document_alignment_options": ["identical-names", "similar-names"],
    "sentence_alignment_options": ["one-to-one", "length-based", "hunalign", "bisent"],
    "sentence_splitter_options": ["europarl", "lingua", "udpipe", "opennlp"]
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash("You need to login first")
            return redirect(url_for('login_page'))
        
    return wrap

def get_group_owner(group, username):
    groupXml = rh.get("/group/"+html.escape(group), {"uid": username})
    parser = xml_parser.XmlParser(groupXml.split("\n"))
    owner = parser.getGroupOwner()
    return owner
    
def get_from_api_and_parse(path, parameters, function):
    rawXml = rh.get(path, parameters)
    parser = xml_parser.XmlParser(rawXml.split("\n"))
    parser_functions = {
        "corporaForUser": parser.corporaForUser,
        "groupsForUser": parser.groupsForUser,
        "getMetadata": parser.getMetadata,
        "getUsers": parser.getUsers,
        "branchesForCorpus": parser.branchesForCorpus,
        "navigateDirectory": parser.navigateDirectory,
        "getMonolingualAndParallel": parser.getMonolingualAndParallel,
        "getAlignCandidates": parser.getAlignCandidates,
        "getJobs": parser.getJobs,
        "getJobPath": parser.getJobPath,
        "getFileContent": parser.getFileContent,
        "itemExists": parser.itemExists
    }
    data = parser_functions[function]()
    return data

@app.route('/')
@login_required
def index():
    if session:
        username = session['username']

    corpora = get_from_api_and_parse("/metadata", {"uid": username, "owner": username, "resource-type": "branch"}, "corporaForUser")
    corpora.sort()
    groups = get_from_api_and_parse("/group/"+username, {"uid": username, "action": "showinfo"}, "groupsForUser")
    groups.sort()

    jobs = get_from_api_and_parse("/job", {"uid": username}, "getJobs")

    groupsAndOwners = []
    for group in groups:
        owner = get_group_owner(group, username)
        groupsAndOwners.append((group, owner))

    return render_template("frontpage.html", corpora=corpora, groups=groupsAndOwners, jobs=jobs)

def initialize_field_dict():
    field_dict = {
        "group": ["gid", "public"],
        "domain": ["domain", ""],
        "origin": ["origin", ""],
        "description": ["description", ""],
        "pdf_reader": ["ImportPara_mode", "tika"],
        "document_alignment": ["AlignPara_search_parallel", "identical-names"],
        "sentence_alignment": ["AlignPara_method", "bisent"],
        "sentence_splitter": ["ImportPara_splitter", "udpipe"],
        "autoalignment": ["ImportPara_autoalign", "on"]
        #"autoparsing": ["ImportPara_autoparse", "on"],
        #"autowordalign": ["ImportPara_autowordalign", "on"]
    }

    return field_dict

@app.route('/create_corpus', methods=["GET", "POST"])
@login_required
def create_corpus():
    if session:
        username = session['username']

    groups = get_from_api_and_parse("/group/"+username, {"uid": username, "action": "showinfo"}, "groupsForUser")
    groups.sort()

    field_dict = initialize_field_dict()
    if request.method == "POST":
        corpusName = html.escape(request.form["name"])

        for key in field_dict.keys():
            #if key in ["autoalignment", "autoparsing", "autowordalign"]:
            if key == "autoalignment":
                field_dict[key][1] = "on"
                if key not in request.form.keys():
                    field_dict[key][1] = "off"
            else:
                field_dict[key][1] = request.form[key]

        if corpusName == "" or " " in corpusName or not all(ord(char) < 128 for char in corpusName):
            
            flash("Name must be ASCII only and must not contain spaces")

            return render_template("create_corpus.html", groups=groups, name=corpusName, settings=field_dict, ftype="create", corpus_creation_options=corpus_creation_options)

        parameters = {"uid": username}

        if get_from_api_and_parse("/storage/"+corpusName, parameters, "itemExists"):
            flash('Corpus "' + corpusName + '" already exists!')
            return render_template("create_corpus.html", groups=groups, name=corpusName, settings=field_dict, ftype="create", corpus_creation_options=corpus_creation_options)

        response = rh.post("/storage/"+corpusName+"/"+username, parameters)

        for key in field_dict.keys():
            parameters[field_dict[key][0]] = html.escape(field_dict[key][1])
        
        response = rh.post("/metadata/"+corpusName+"/"+username, parameters)
            
        flash('Corpus "' + html.unescape(corpusName) + '" created!')
        return redirect(url_for('show_corpus', corpusname=html.unescape(corpusName)))

    return render_template("create_corpus.html", groups=groups, ftype="create", settings=field_dict, corpus_creation_options=corpus_creation_options)

@app.route('/corpus_settings/<corpusname>', methods=["GET", "POST"])
@login_required
def corpus_settings(corpusname):
    if session:
        username = session['username']

    groups = get_from_api_and_parse("/group/"+username, {"uid": username, "action": "showinfo"}, "groupsForUser")
    groups.sort()

    metadata = get_from_api_and_parse("/metadata/"+html.escape(corpusname)+"/"+username, {"uid": username}, "getMetadata")

    field_dict = initialize_field_dict() 

    for key in field_dict.keys():
        if field_dict[key][0] in metadata.keys():
            field_dict[key][1] = html.unescape(metadata[field_dict[key][0]])
        else:
            field_dict[key][1] = "off"

    if request.method == "POST":
        parameters = {"uid": username}
        
        for key in field_dict.keys():
            if key in request.form.keys():
                parameters[field_dict[key][0]] = html.escape(request.form[key])
            else:
                parameters[field_dict[key][0]] = "off"

        response = rh.post("/metadata/"+html.escape(corpusname)+"/"+username, parameters)
            
        flash('Corpus settings saved!')
        return redirect(url_for('show_corpus', corpusname=corpusname))
 
    return render_template("create_corpus.html", groups=groups, name=corpusname, settings=field_dict, ftype="settings", corpus_creation_options=corpus_creation_options)

@app.route('/remove_corpus')
@login_required
def remove_corpus():
    if session:
        username = session['username']

    corpusname = request.args.get("tobedeleted", "", type=str)
    response = rh.delete("/storage/"+html.escape(corpusname)+"/"+username, {"uid": username})

    return jsonify(response=response)

@app.route('/remove_group')
@login_required
def remove_group():
    if session:
        username = session['username']

    groupname = request.args.get("tobedeleted", "", type=str)
    response = rh.delete("/group/"+html.escape(groupname), {"uid": username})

    return jsonify(response=response)

def get_group_members(group, username):
    users = get_from_api_and_parse("/group/"+html.escape(group), {"uid": username, "action": "showinfo"}, "getUsers")
    for user in ["admin", username]:
        if user in users:
            users.remove(user)
    users.sort()
    return users

@app.route('/create_group', methods=["GET", "POST"])
@login_required
def create_group():
    if session:
        username = session['username']

    users = get_group_members("public", username)

    if request.method == "POST":
        groupName = html.escape(request.form["name"])
        members = request.form["members"].split(",")[:-1]
                    
        if groupName == "" or " " in groupName or not all(ord(char) < 128 for char in groupName):
            flash("Name must be ASCII only and must not contain spaces")
            return render_template("create_group.html", name=request.form['name'], members=members, users=users, owner=True)

        if get_from_api_and_parse("/group/"+groupName, {"uid": username}, "itemExists"):
            flash('Group "' + groupName + '" already exists!')
            return render_template("create_group.html", name=request.form['name'], members=members, users=users, owner=True)

        response = rh.post("/group/"+groupName, {"uid": username})
        
        for member in members:
            response = rh.put("/group/"+groupName+"/"+member, {"uid": username})

        flash('Group "' + html.unescape(groupName) + '" created!')
        return redirect(url_for('index'))

    return render_template("create_group.html", users=users, owner=True)

@app.route('/edit_group/<groupname>', methods=["GET", "POST"])
@login_required
def edit_group(groupname):
    if session:
        username = session['username']
        
    users = get_group_members("public", username)
    current_members = get_group_members(groupname, username)
    groupowner = get_group_owner(groupname, username)
    owner = groupowner == username
    if groupname == username:
        owner = False

    if request.method == "POST":
        for member in current_members:
            response = rh.delete("/group/"+groupname+"/"+member, {"uid": username})

        members = request.form["members"].split(",")[:-1]
        for member in members:
            response = rh.put("/group/"+groupname+"/"+member, {"uid": username})

        flash('Changes saved!')
        return redirect(url_for('edit_group', groupname=groupname))

    return render_template("create_group.html", users=users, name=groupname, members=current_members, owner=owner, edit=True)

@app.route('/show_corpus/<corpusname>')
@login_required
def show_corpus(corpusname):
    if session:
        username = session['username']

    branches = get_from_api_and_parse("/storage/"+html.escape(corpusname), {"uid": username}, "branchesForCorpus")
    branches.sort()
    
    clone = False
    if username not in branches:
        clone = True
    
    return render_template("show_corpus.html", name=corpusname, branches=branches, clone=clone)

@app.route('/download_file')
@login_required
def download_file():
    if session:
        username = session['username']

    path = request.args.get("path", "", type=str)
    filename = request.args.get("filename", "", type=str)

    ret = rh.get("/storage"+path, {"uid": username, "action": "download", "archive": "0"})

    timename = str(time.time())+"###TIME###"+filename
    global previous_download
    if previous_download != "":
        os.remove(download_folder+"/"+previous_download)
    previous_download = timename
    with open(download_folder+"/"+timename, "w") as f:
        f.write(ret)
    return send_from_directory(download_folder+"/", timename, as_attachment=True, attachment_filename=filename)
        
@app.route('/clone_branch')
@login_required
def clone_branch():
    if session:
        username = session['username']
    corpusname = request.args.get("corpusname", "", type=str)
    branch = request.args.get("branchclone", "", type=str)
    path = corpusname + "/" + branch
    
    ret = rh.post("/storage/"+path, {"uid": username, "action": "copy", "dest": username})

    branches = get_from_api_and_parse("/storage/"+corpusname, {"uid": username}, "branchesForCorpus")
    branches.sort()
        
    clone = False
    if username not in branches:
        clone = True

    flash('Copied branch "'+path+'" to "'+corpusname+"/"+username+'"')
    
    return render_template("show_corpus.html", name=corpusname, branches=branches, clone=clone)
    
@app.route('/search')
@login_required
def search():
    if session:
        username = session['username']

    corpusname = html.escape(request.args.get("corpusname", "", type=str))

    unsorted = get_from_api_and_parse("/metadata", {"uid": username, "resource-type": "branch", "INCLUDES_slot": corpusname}, "corporaForUser")

    starts = []
    contains = []
    for corpus in unsorted:
        if corpus.startswith(corpusname):
            starts.append(html.unescape(corpus))
        else:
            contains.append(html.unescape(corpus))
            
    starts.sort()
    contains.sort()
    
    corpora = starts + contains

    return jsonify(result=corpora)

@app.route('/update_metadata')
@login_required
def update_metadata():
    if session:
        username = session['username']
    path = request.args.get("path", "", type=str)
    metadata = request.args.get("changes", "", type=str)
    metadata = json.loads(metadata)
    
    for key in metadata.keys():
        metadata[key] = html.escape(metadata[key])
    metadata["uid"] = username
    response = rh.post("/metadata"+path, metadata)

    return jsonify(response=response)
        
@app.route('/edit_alignment')
@login_required
def edit_alignment():
    if session:
        username = session['username']
    path = request.args.get("path", "", type=str)
    response = rh.put("/job"+path, {"uid": username, "run": "setup_isa"})

    return jsonify(response=response, username=username)

@app.route('/get_branch')
@login_required
def get_branch():
    uploads = []
    monolingual = []
    parallel = []
    
    branch = request.args.get("branch", "", type=str)
    corpusname = request.args.get("corpusname", "", type=str)

    if session:
        username = session['username']

    owner = username == branch

    uploads = get_from_api_and_parse("/storage/"+corpusname+"/"+branch+"/uploads", {"uid": username}, "navigateDirectory")
    
    monolingual, parallel = get_from_api_and_parse("/metadata/"+corpusname+"/"+branch, {"uid": username}, "getMonolingualAndParallel")
    monolingual.sort()
    parallel.sort()
    
    return jsonify(uploads=uploads, parallel=parallel, monolingual=monolingual, owner=owner)

@app.route('/get_subdirs')
@login_required
def get_subdirs():
    subdirs = []
    
    branch = request.args.get("branch", "", type=str)
    corpusname = request.args.get("corpusname", "", type=str)
    subdir = request.args.get("subdir", "", type=str)

    if session:
        username = session['username']

    subdir = subdir.replace("-_-", "/")
    subdir = subdir.replace("-_DOT_-", ".")
    subdir = subdir.replace("monolingual", "xml")
    subdir = subdir.replace("align-source-files", "xml")
    subdir = subdir.replace("align-target-files", "xml")
    subdir = subdir.replace("parallel", "xml")

    subdirs = get_from_api_and_parse("/storage/"+corpusname+"/"+branch+subdir, {"uid": username}, "navigateDirectory")
    subdirs.sort()
    
    return jsonify(subdirs=subdirs)

@app.route('/upload_file', methods=['GET', 'POST'])
@login_required
def upload_file():
    if session:
        username = session['username']

    if request.method == 'POST':
        path = request.form['path']
        m = re.search("^\/(.*?)\/(.*?)\/", path)
        if m:
            corpus = m.group(1)
            branch = m.group(2)
            if branch != username:
                flash("Invalid branch name")
                return redirect(url_for("upload_file", corpus=corpus, branch=username))
        else:
            flash("Invalid upload path")
            return redirect(url_for("index"))
        language = "detect"
        if "language" in request.form.keys():
            language = request.form['language']
        description = request.form['description']
        direction = "unknown"
        autoimport = "false"
        if "direction" in request.form.keys():
            direction = request.form["direction"]
        if "autoimport" in request.form.keys():
            autoimport = "true"
        if 'file' not in request.files:
            flash('No file part')
            return redirect(url_for("upload_file", corpus=corpus, branch=branch, language=language, description=description, direction=direction, autoimport=autoimport))
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(url_for("upload_file", corpus=corpus, branch=branch, language=language, description=description, direction=direction, autoimport=autoimport))
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            timename = str(time.time())+"###TIME###"+filename
            path = "/".join(request.form['path'].split("/")[:-1])+"/"+filename

            if get_from_api_and_parse("/storage"+path, {"uid": username}, "itemExists"):
                flash('File "' + path + '" already exists!')
                return redirect(url_for("upload_file", corpus=corpus, branch=branch, language=language, description=description, direction=direction, autoimport=autoimport))

            description = request.form['description']
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], timename))

            upload_param = {"uid": username}
            if "autoimport" in request.form.keys():
                upload_param["action"] = "import"

            ret = rh.upload("/storage" + path, upload_param, UPLOAD_FOLDER+"/"+timename)

            response = rh.put("/metadata"+path, {"uid": username, "description": html.escape(description), "direction": direction})

            os.remove(UPLOAD_FOLDER + "/" + timename)
            flash('Uploaded file "' + filename + '" to "' + path + '"')

            return redirect(url_for('upload_file', corpus=corpus, branch=branch))
        else:
            flash('File format is not allowed')
            return redirect(url_for("upload_file", corpus=corpus, branch=branch, language=language, description=description, direction=direction, autoimport=autoimport))

    return render_template("upload_file.html", languages=iso639_1)
        
@app.route('/get_metadata')
@login_required
def get_metadata():
    if session:
        username = session['username']

    path = request.args.get("path", "", type=str)

    metadata = get_from_api_and_parse("/metadata"+path, {"uid": username}, "getMetadata")
    metadataKeys = list(metadata.keys()).copy()
    metadataKeys.sort()

    return jsonify(metadata = metadata, metadataKeys = metadataKeys, username = username)

@app.route('/get_filecontent')
@login_required
def get_filecontent():
    if session:
        username = session['username']

    path = request.args.get("path", "", type=str)

    content = get_from_api_and_parse("/storage"+path, {"uid": username, "action": "cat", "to": "1000"}, "getFileContent")

    return jsonify(content = content)

@app.route('/import_file')
@login_required
def import_file():
    if session:
        username = session['username']

    path = request.args.get("path", "", type=str)
    command = request.args.get("command", "", type=str)
    if command in ["import", "import again"]:
        response = rh.put("/job"+path, {"uid": username, "run": "reimport"})
    elif command in ["stop importing", "cancel import"]:
        metadata = get_from_api_and_parse("/metadata"+path, {"uid": username}, "getMetadata")
        job_id = metadata["job_id"]
        response = rh.delete("/job", {"uid": username, "job_id": job_id})
    
    return jsonify(content = response)

@app.route('/delete_file')
@login_required
def delete_file():
    if session:
        username = session['username']

    path = request.args.get("path", "", type=str)
    response = rh.delete("/storage"+path, {"uid": username})
    path = path.replace("/xml/", "/tmx/")
    rh.delete("/storage"+path, {"uid": username})

    return jsonify(content = response)

@app.route('/list_alignment_candidates')
@login_required
def list_alignment_candidates():
    if session:
        username = session['username']

    corpus = request.args.get("corpus", "", type=str)
    branch = request.args.get("branch", "", type=str)

    candidates = get_from_api_and_parse("/metadata/"+corpus+"/"+branch, {"uid": username, "ENDS_WITH_align-candidates": "xml", "type": "recursive", "action": "list_all"}, "getAlignCandidates")
    file_list = list(candidates.keys())
    file_list.sort()
    return jsonify(candidates = candidates, file_list = file_list)

@app.route('/find_alignment_candidates')
@login_required
def find_alignment_candidates():
    if session:
        username = session['username']

    corpus = request.args.get("corpus", "", type=str)
    branch = request.args.get("branch", "", type=str)

    response = rh.put("/job/"+corpus+"/"+branch+"/xml", {"uid": username, "run": "detect_translations"})

    return jsonify(content = response)
    
def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc

@app.route('/remove_alignment_candidate')
@login_required
def remove_alignment_candidate():
    if session:
        username = session['username']

    filename = request.args.get("filename", "", type=str)
    rm_candidate = request.args.get("rm_candidate", "", type=str)

    candidates = get_from_api_and_parse("/metadata/"+filename, {"uid": username}, "getAlignCandidates")
    temp_candidates = candidates[list(candidates.keys())[0]]
    cur_candidates = ["xml/"+c for c in temp_candidates]
    cur_candidates.remove(rm_candidate)
    response = rh.post("/metadata/"+filename, {"uid": username, "align-candidates": ",".join(cur_candidates)})

    return jsonify(content=response)

@app.route('/add_alignment_candidate')
@login_required
def add_alignment_candidate():
    if session:
        username = session['username']

    filename = request.args.get("filename", "", type=str)
    add_candidate = request.args.get("add_candidate", "", type=str)

    response = rh.put("/metadata/"+filename, {"uid": username, "align-candidates": add_candidate})

    return jsonify(content=response)

@app.route('/align_candidates')
@login_required
def align_candidates():
    if session:
        username = session['username']
    filesdata = request.args.get("files", "", type=str)

    files = json.loads(filesdata);

    for filename in files.keys():
        response = rh.put("/job/"+filename, {"uid": username, "trg": files[filename], "run": "align"})

    return jsonify(content=response)

@app.route('/login/', methods=["GET", "POST"])
def login_page():
    error = ''
    try:
        c, conn = connection()
        if request.method == "POST":
            data = c.execute("SELECT * FROM users WHERE username = (%s)",
                             thwart(request.form['username']))
            
            data = c.fetchone()['password']
            
            if sha256_crypt.verify(request.form['password'], data):
                session['logged_in'] = True
                session['username'] = request.form['username']
                
                flash("You are now logged in")

                next_url = request.args.get('next')

                if not is_safe_url(next_url):
                    return flask.abort(400)

                return redirect(url_for("index"))
            
            else:
                error = "Invalid credentials, try again."
                
        gc.collect()
                
        return render_template("login.html", error=error)

    except Exception as e:
        error = "Invalid credentials, try again."
        return render_template("login.html", error=error)

class RegistrationForm(Form):
    username = StringField('Username', [validators.Length(min=4, max=20)])
    email = StringField('Email Address', [validators.Length(min=6, max=50)])
    password = PasswordField('New Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords must match')
    ])
    confirm = PasswordField('Repeat Password')
    
@app.route('/register/', methods=["GET", "POST"])
def register_page():
    try:
        form = RegistrationForm(request.form)

        if request.method == "POST" and form.validate():
            username = form.username.data
            email = form.email.data
            password = sha256_crypt.hash((str(form.password.data)))
            c, conn = connection()

            x =  c.execute("SELECT * FROM users WHERE username = (%s)", (thwart(username)))

            if int(x) > 0:
                error = "That username is already taken, please choose another"
                return render_template('register.html', form=form, error=error)

            else:
                c.execute("INSERT INTO users (username, password, email, tracking) VALUES (%s, %s, %s, %s)",
                         (thwart(username), thwart(password), thwart(email), thwart("translate")))
                response = rh.post("/group/"+thwart(username), {"uid": thwart(username)})
                conn.commit()
                flash("Thanks for registering!")
                c.close()
                conn.close()
                gc.collect()

                session['logged_in'] = True
                session['username'] = username

                return redirect(url_for('index'))

        return render_template("register.html", form=form)

    except Exception as e:
        return(str(e))

@app.route("/logout/")
@login_required
def logout():
    session.clear()
    flash("You have been logged out!")
    gc.collect()
    return redirect(url_for('login_page'))

if __name__=='__main__':
    app.run()
