from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, send_file, send_from_directory
from wtforms import Form, BooleanField, TextField, PasswordField, validators
from passlib.hash import sha256_crypt
from pymysql import escape_string as thwart
import gc
from dbconnect import connection
from functools import wraps
import sqlite3
from sqlalchemy import create_engine
import pickle
import subprocess as sp
import os
from werkzeug.utils import secure_filename
import time
import xml_parser
import re
from urllib.parse import urlparse, urljoin
import request_handler
import json

import traceback

rh = request_handler.RequestHandler()

UPLOAD_FOLDER = "/home/cloud-user/uploads"
download_folder= "/home/cloud-user/downloads"
ALLOWED_EXTENSIONS = set(['txt', 'xml', 'html', 'tar', 'gz'])

app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

with open("secrets/secretkey") as f:
    key = f.read()[:-1].encode("utf-8")
app.secret_key = key

letsmt_connect = "curl --silent --show-error --cacert /var/www/cert/vm1637.kaj.pouta.csc.fi/ca.crt --cert /var/www/cert/vm1637.kaj.pouta.csc.fi/user/certificates/developers@localhost.crt:letsmt --key /var/www/cert/vm1637.kaj.pouta.csc.fi/user/keys/developers@localhost.key"

letsmt_url = "https://vm1637.kaj.pouta.csc.fi:443/ws"

previous_download = ""

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
    groupXml = rh.get("/group/"+group, {"uid": username})
    parser = xml_parser.XmlParser(groupXml.split("\n"))
    owner = parser.getGroupOwner()
    return owner
    
@app.route('/')
@login_required
def index():
    if session:
        username = session['username']

    corporaXml = rh.get("/metadata", {"uid": username, "owner": username, "resource-type": "branch"})
    parser = xml_parser.XmlParser(corporaXml.split("\n"))
    corpora = parser.corporaForUser()
    corpora.sort()

    groupsXml = rh.get("/group/"+username, {"uid": username, "action": "showinfo"})
    parser = xml_parser.XmlParser(groupsXml.split("\n"))
    groups = parser.groupsForUser()
    groups.sort()

    groupsAndOwners = []
    for group in groups:
        owner = get_group_owner(group, username)
        groupsAndOwners.append((group, owner))

    return render_template("frontpage.html", corpora=corpora, groups=groupsAndOwners)

@app.route('/create_corpus', methods=["GET", "POST"])
@login_required
def create_corpus():
    if session:
        username = session['username']

    groupsXml = rh.get("/group/"+username, {"uid": username, "action": "showinfo"})
    parser = xml_parser.XmlParser(groupsXml.split("\n"))
    groups = parser.groupsForUser()
    groups.sort()

    if request.method == "POST":
        print(request.form)
        corpusName = request.form["name"]
        if corpusName == "" or " " in corpusName or not all(ord(char) < 128 for char in corpusName):
            autoalignment = False
            if "autoalignment" in request.form.keys():
                autoalignment = True
            flash("Name must be ASCII only and must not contain spaces")
            return render_template("create_corpus.html", groups=groups, name=request.form['name'], domain=request.form['domain'], origin=request.form['origin'], description=request.form['description'], selectedgroup=request.form['group'], autoalignment=autoalignment, ftype="create")

        parameters = {"uid": username}
        if request.form["group"] != "public":
            parameters["gid"] = request.form["group"]
        response = rh.put("/storage/"+corpusName+"/"+username, parameters)

        try:
            parameters = {"uid": username}
            for key in request.form.keys():
                if key in ["origin", "domain", "description"]:
                    parameters[key] = request.form[key]

            if "autoalignment" not in request.form.keys():
                parameters["ImportPara_autoalign"] = "off"

            response = rh.put("/metadata/"+corpusName+"/"+username, parameters)
        except:
            traceback.print_exc()
            
        flash('Corpus "' + corpusName + '" created!')
        return redirect(url_for('show_corpus', corpusname=corpusName))

    return render_template("create_corpus.html", groups=groups, ftype="create", autoalignment=True)

@app.route('/remove_corpus')
@login_required
def remove_corpus():
    if session:
        username = session['username']

    corpusname = request.args.get("tobedeleted", "", type=str)
    response = rh.delete("/storage/"+corpusname+"/"+username, {"uid": username})

    return jsonify(response=response)

@app.route('/remove_group')
@login_required
def remove_group():
    if session:
        username = session['username']

    groupname = request.args.get("tobedeleted", "", type=str)
    response = rh.delete("/group/"+groupname, {"uid": username})

    return jsonify(response=response)

@app.route('/corpus_settings/<corpusname>', methods=["GET", "POST"])
@login_required
def corpus_settings(corpusname):
    if session:
        username = session['username']

    groupsXml = rh.get("/group/"+username, {"uid": username, "action": "showinfo"})
    parser = xml_parser.XmlParser(groupsXml.split("\n"))
    groups = parser.groupsForUser()
    groups.sort()

    metadataXml = rh.get("/metadata/"+corpusname+"/"+username, {"uid": username})
    parser = xml_parser.XmlParser(metadataXml.split("\n"))
    metadata = parser.getMetadata()

    setting_fields = {"domain": "", "origin": "", "description": ""}
    for key in setting_fields.keys():
        if key in metadata.keys():
            setting_fields[key] = metadata[key]

    setting_fields["autoalignment"] = False
    if "ImportPara_autoalign" not in metadata.keys() or ("ImportPara_autoalign" in metadata.keys() and metadata["ImportPara_autoalign"] == "on"):
        setting_fields["autoalignment"] = True
    
    if request.method == "POST":
        print(request.form)
        parameters = {"uid": username}
        if request.form["group"] != "public":
            parameters["gid"] = request.form["group"]

        try:
            parameters["ImportPara_autoalign"] = "on"
            if "autoalignment" not in request.form.keys():
                parameters["ImportPara_autoalign"] = "off"
                
            for key in request.form.keys():
                if key in ["origin", "domain", "description"]:
                    parameters[key] = request.form[key]

            response = rh.post("/metadata/"+corpusname+"/"+username, parameters)
        except:
            traceback.print_exc()
            
        flash('Corpus settings saved!')
        return redirect(url_for('show_corpus', corpusname=corpusname))

    return render_template("create_corpus.html", groups=groups, name=corpusname, domain=setting_fields["domain"], origin=setting_fields["origin"], description=setting_fields["description"], autoalignment=setting_fields["autoalignment"], ftype="settings")

def get_group_members(group, username):
    usersXml = rh.get("/group/"+group, {"uid": username, "action": "showinfo"})
    parser = xml_parser.XmlParser(usersXml.split("\n"))
    users = parser.getUsers()
    for user in ["admin", username]:
        if user in users:
            users.remove(user)
    users.sort()
    return users

@app.route('/create_group', methods=["GET", "POST"])
@login_required
def create_group():
    try:
        if session:
            username = session['username']

        users = get_group_members("public", username)

        if request.method == "POST":
            groupName = request.form["name"]
            members = request.form["members"].split(",")[:-1]
                        
            if groupName == "" or " " in groupName or not all(ord(char) < 128 for char in groupName):
                flash("Name must be ASCII only and must not contain spaces")
                return render_template("create_group.html", name=request.form['name'], members=members, users=users, owner=True)

            response = rh.post("/group/"+groupName, {"uid": username})
            
            for member in members:
                response = rh.put("/group/"+groupName+"/"+member, {"uid": username})

            flash('Group "' + groupName + '" created!')
            return redirect(url_for('index'))

        return render_template("create_group.html", users=users, owner=True)
    except:
        traceback.print_exc()

@app.route('/edit_group/<groupname>', methods=["GET", "POST"])
@login_required
def edit_group(groupname):
    try:
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
    except:
        traceback.print_exc()

@app.route('/show_corpus/<corpusname>')
@login_required
def show_corpus(corpusname):
    try:
        if session:
            username = session['username']

        branchesXml = rh.get("/storage/"+corpusname, {"uid": username})
        parser = xml_parser.XmlParser(branchesXml.split("\n"))
        branches = parser.branchesForCorpus()
        branches.sort()
        
        clone = False
        if username not in branches:
            clone = True
    except:
        traceback.print_exc()
    
    return render_template("show_corpus.html", name=corpusname, branches=branches, clone=clone)

@app.route('/download/<filename>')
def download(filename):
    try:
        if session:
            username = session['username']

        ret = rh.get("/storage/mikkoslot/xml/en/html/"+filename, {"uid": username, "action": "download", "archive": "0"})
        timename = str(time.time())+"###TIME###"+filename
        global previous_download
        if previous_download != "":
            os.remove(download_folder+"/"+previous_download)
        previous_download = timename
        with open(download_folder+"/"+timename, "w") as f:
            f.write(ret)
        return send_file(download_folder+"/"+timename, attachment_filename=filename)
    except:
        traceback.print_exc()

@app.route('/download_file')
@login_required
def download_file():
    try:
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
    except:
        traceback.print_exc()
        
@app.route('/clone_branch')
@login_required
def clone_branch():
    if session:
        username = session['username']
    corpusname = request.args.get("corpusname", "", type=str)
    branch = request.args.get("branchclone", "", type=str)
    path = corpusname + "/" + branch
    
    ret = rh.post("/storage/"+path, {"uid": username, "action": "copy", "dest": username})

    branchesXml = rh.get("/storage/"+corpusname, {"uid": username})
    parser = xml_parser.XmlParser(branchesXml.split("\n"))
    branches = parser.branchesForCorpus()
    branches.sort()
        
    clone = False
    if username not in branches:
        clone = True

    flash('Copied branch "'+path+'" to "'+corpusname+"/"+username+'"')
    
    return render_template("show_corpus.html", name=corpusname, branches=branches, clone=clone)
    
@app.route('/search')
@login_required
def search():
    try:
        if session:
            username = session['username']

        corpusname = request.args.get("corpusname", "", type=str)

        corporaXml = rh.get("/metadata", {"uid": username, "resource-type": "branch", "INCLUDES_slot": corpusname})
        
        parser = xml_parser.XmlParser(corporaXml.split("\n"))
        unsorted = parser.corporaForUser()

        starts = []
        contains = []
        for corpus in unsorted:
            if corpus.startswith(corpusname):
                starts.append(corpus)
            else:
                contains.append(corpus)
                
        starts.sort()
        contains.sort()
        
        corpora = starts + contains

        return jsonify(result=corpora)
    except:
        traceback.print_exc()

@app.route('/update_metadata')
@login_required
def update_metadata():
    try:
        if session:
            username = session['username']
        path = request.args.get("path", "", type=str)
        metadata = request.args.get("changes", "", type=str)
        metadata = json.loads(metadata)

        metadata["uid"] = username
        response = rh.post("/metadata"+path, metadata)

        return jsonify(response=response)
    except:
        traceback.print_exc()
        
@app.route('/edit_alignment')
@login_required
def edit_alignment():
    try:
        if session:
            username = session['username']
        path = request.args.get("path", "", type=str)
        response = rh.put("/job"+path, {"uid": username, "run": "setup_isa"})

        return jsonify(response=response, username=username)
    except:
        traceback.print_exc()
           
@app.route('/letsmtui', methods=['GET', 'POST'])
@login_required
def letsmtui():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            timename = str(time.time())+"###TIME###"+filename
            directory = request.form['directory']
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], timename))
            if session:
                username = session['username']
            try:
                command = letsmt_connect.split() + ["-X", "PUT", letsmt_url + directory + "?uid=" + username, "--form", "payload=@/var/www/uploads/"+timename]
                ret = sp.Popen(command , stdout=sp.PIPE).stdout.read().decode("utf-8")
            except:
                traceback.print_exc()
            os.remove("/var/www/uploads/" + timename)
            flash("Uploaded file " + filename + " to " + directory)
            return redirect(url_for('letsmtui', directory=directory))
    return render_template("letsmt.html")

@app.route('/letsmt')
@login_required
def letsmt():
    try:
        ret = ""

        method = request.args.get("method", "GET", type=str)
        command = request.args.get("command", "/storage", type=str)
        action = request.args.get("action", "", type=str)
        payload = request.args.get("payload", "", type=str)
        if payload != "":
            payload = " --form payload=@/var/www/uploads/" + payload
        username = ""
        if session:
            username = session['username']
        ret = sp.Popen(letsmt_connect.split() + ["-X", method, letsmt_url+command+"?uid=" + username + action + payload], stdout=sp.PIPE).stdout.read().decode("utf-8")
        return jsonify(result=ret)
    except Exception:
        traceback.print_exc()


@app.route('/get_branch')
@login_required
def get_branch():
    try:
        uploads = []
        monolingual = []
        parallel = []
        
        branch = request.args.get("branch", "", type=str)
        corpusname = request.args.get("corpusname", "", type=str)

        if session:
            username = session['username']

        uploadsContents = rh.get("/storage/"+corpusname+"/"+branch+"/uploads", {"uid": username})
        parser = xml_parser.XmlParser(uploadsContents.split("\n"))
        uploads = parser.navigateDirectory()

        xmlContents = rh.get("/metadata/"+corpusname+"/"+branch, {"uid": username})
        parser = xml_parser.XmlParser(xmlContents.split("\n"))
        monolingual, parallel = parser.getMonolingualAndParallel()
        monolingual.sort()
        parallel.sort()
        
        return jsonify(uploads=uploads, parallel=parallel, monolingual=monolingual)
    except Exception:
        traceback.print_exc()

@app.route('/get_subdirs')
@login_required
def get_subdirs():
    try:
        subdirs = []
        
        branch = request.args.get("branch", "", type=str)
        corpusname = request.args.get("corpusname", "", type=str)
        subdir = request.args.get("subdir", "", type=str)

        if session:
            username = session['username']

        subdir = subdir.replace("-_-", "/")
        subdir = subdir.replace("monolingual", "xml")
        subdir = subdir.replace("align-source-files", "xml")
        subdir = subdir.replace("align-target-files", "xml")
        subdir = subdir.replace("parallel", "xml")

        subdirContents = rh.get("/storage/"+corpusname+"/"+branch+subdir, {"uid": username})
        parser = xml_parser.XmlParser(subdirContents.split("\n"))
        subdirs = parser.navigateDirectory()
        subdirs.sort()
        
        return jsonify(subdirs=subdirs)
    except Exception:
        traceback.print_exc()

@app.route('/upload_file', methods=['GET', 'POST'])
@login_required
def upload_file():
    try:
        if request.method == 'POST':
            path = request.form['path']
            m = re.search("^\/(.*?)\/(.*?)\/", path)
            corpus = m.group(1)
            branch = m.group(2)
            language = ""
            if "language" in request.form.keys():
                language = request.form['language']
            fileformat = request.form['format']
            description = request.form['description']
            direction = "unknown"
            autoimport = "false"
            if "direction" in request.form.keys():
                direction = request.form["direction"]
            if "autoimport" in request.form.keys():
                autoimport = "true"
            if 'file' not in request.files:
                flash('No file part')
                return redirect(url_for("upload_file", corpus=corpus, branch=branch, language=language, fileformat=fileformat, description=description, direction=direction, autoimport=autoimport))
            file = request.files['file']
            if file.filename == '':
                flash('No selected file')
                return redirect(url_for("upload_file", corpus=corpus, branch=branch, language=language, fileformat=fileformat, description=description, direction=direction, autoimport=autoimport))
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timename = str(time.time())+"###TIME###"+filename
                path = request.form['path']
                description = request.form['description']
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], timename))
                if session:
                    username = session['username']

                ret = rh.upload("/storage" + path, {"uid": username}, UPLOAD_FOLDER+"/"+timename)

                if "autoimport" in request.form.keys():
                    response = rh.put("/job"+path, {"uid": username, "run": "import"})

                response = rh.put("/metadata"+path, {"uid": username, "description": description, "direction": direction})

                os.remove(UPLOAD_FOLDER + "/" + timename)
                flash('Uploaded file "' + filename + '" to "' + path + '"')

                return redirect(url_for('show_corpus', corpusname=corpus, branch=branch))

        return render_template("upload_file.html", formats=["txt", "html", "pdf", "doc", "tar"], languages=["da", "en", "fi", "no", "sv"])
    except:
        traceback.print_exc()
        
@app.route('/get_metadata')
@login_required
def get_metadata():
    try:
        if session:
            username = session['username']

        path = request.args.get("path", "", type=str)

        metadataXml = rh.get("/metadata"+path, {"uid": username})
        parser = xml_parser.XmlParser(metadataXml.split("\n"))
        metadata = parser.getMetadata()
        metadataKeys = list(metadata.keys()).copy()
        metadataKeys.sort()

        return jsonify(metadata = metadata, metadataKeys = metadataKeys, username = username)

    except:
        traceback.print_exc()

@app.route('/get_filecontent')
@login_required
def get_filecontent():
    if session:
        username = session['username']

    path = request.args.get("path", "", type=str)
    content = rh.get("/storage"+path, {"uid": username, "action": "download", "archive": "0"})
    
    return jsonify(content = content)

@app.route('/import_file')
@login_required
def import_file():
    if session:
        username = session['username']

    path = request.args.get("path", "", type=str)
    response = rh.put("/job"+path, {"uid": username, "run": "reimport"})
    
    return jsonify(content = response)

@app.route('/delete_file')
@login_required
def delete_file():
    if session:
        username = session['username']

    path = request.args.get("path", "", type=str)
    response = rh.delete("/storage"+path, {"uid": username})

    return jsonify(content = response)

@app.route('/list_alignment_candidates')
@login_required
def list_alignment_candidates():
    try:
        if session:
            username = session['username']

        corpus = request.args.get("corpus", "", type=str)
        branch = request.args.get("branch", "", type=str)

        candidates_xml = rh.get("/metadata/"+corpus+"/"+branch, {"uid": username, "ENDS_WITH_align-candidates": "xml", "type": "recursive", "action": "list_all"})
        parser = xml_parser.XmlParser(candidates_xml.split("\n"))
        candidates = parser.getAlignCandidates()
        file_list = list(candidates.keys())
        file_list.sort()
        return jsonify(candidates = candidates, file_list = file_list)
    except:
        traceback.print_exc()

@app.route('/find_alignment_candidates')
@login_required
def find_alignment_candidates():
    try:
        if session:
            username = session['username']

        corpus = request.args.get("corpus", "", type=str)
        branch = request.args.get("branch", "", type=str)

        response = rh.put("/job/"+corpus+"/"+branch+"/xml", {"uid": username, "run": "detect_translations"})

        return jsonify(content = response)
    except:
        traceback.print_exc()
    
def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc

@app.route('/remove_alignment_candidate')
@login_required
def remove_alignment_candidate():
    try:
        if session:
            username = session['username']

        filename = request.args.get("filename", "", type=str)
        rm_candidate = request.args.get("rm_candidate", "", type=str)

        candidates_xml = rh.get("/metadata/"+filename, {"uid": username})
        parser = xml_parser.XmlParser(candidates_xml.split("\n"))
        candidates = parser.getAlignCandidates()
        temp_candidates = candidates[list(candidates.keys())[0]]
        cur_candidates = ["xml/"+c for c in temp_candidates]
        cur_candidates.remove(rm_candidate)
        response = rh.post("/metadata/"+filename, {"uid": username, "align-candidates": ",".join(cur_candidates)})

        return jsonify(content=response)
    except:
        traceback.print_exc()

@app.route('/add_alignment_candidate')
@login_required
def add_alignment_candidate():
    try:
        if session:
            username = session['username']

        filename = request.args.get("filename", "", type=str)
        add_candidate = request.args.get("add_candidate", "", type=str)

        response = rh.put("/metadata/"+filename, {"uid": username, "align-candidates": add_candidate})

        return jsonify(content=response)
    except:
        traceback.print_exc()

@app.route('/align_candidates')
@login_required
def align_candidates():
    try:
        if session:
            username = session['username']
        filesdata = request.args.get("files", "", type=str)

        files = json.loads(filesdata);

        for filename in files.keys():
            response = rh.put("/job/"+filename, {"uid": username, "trg": files[filename], "run": "align"})

        return jsonify(content=response)
    except:
        traceback.print_exc()

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
    username = TextField('Username', [validators.Length(min=4, max=20)])
    email = TextField('Email Address', [validators.Length(min=6, max=50)])
    password = PasswordField('New Password', [
        validators.Required(),
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
            password = sha256_crypt.encrypt((str(form.password.data)))
            c, conn = connection()

            x =  c.execute("SELECT * FROM users WHERE username = (%s)", (thwart(username)))

            if int(x) > 0:
                error = "That username is already taken, please choose another"
                return render_template('register.html', form=form, error=error)

            else:
                c.execute("INSERT INTO users (username, password, email, tracking) VALUES (%s, %s, %s, %s)",
                         (thwart(username), thwart(password), thwart(email), thwart("translate")))
                response = rh.post("/group/"+thwart(username), {"uid": thwart(username)})
                print(response)
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
