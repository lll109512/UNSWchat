#!/web/cs2041/bin/python3.6.3
import os
import random
import re
import time
import threading
import queue
import math
import string
import json
from flask import Flask, request, render_template, session, url_for, redirect, flash
from Helper import DBhelper, Filehelper
from functools import wraps
from Forms import *
from werkzeug.utils import secure_filename
import subprocess
Debug = False

# global EventQueue
# EventQueue = queue.Queue()

page_size = 10

DEFAULT_USER_IMG = 'img/userphotos/default_user.png'
UPLOAD_FOLDER = os.getcwd()+'/static/img/userphotos'
POST_IMG_FOLDER = os.getcwd()+'/static/img/postimg'
SIMILARITY_T = 0
ALLOWED_EXTENSIONS = set(['txt', 'png', 'jpg', 'jpeg', 'gif'])


app = Flask(__name__, template_folder='templates')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['DEFAULT_USER_IMG'] = DEFAULT_USER_IMG
app.config['POST_IMG_FOLDER'] = POST_IMG_FOLDER
app.config['SIMILARITY_T'] = SIMILARITY_T
DB = DBhelper("myuserDB.db", "123", page_size = page_size)


def send_email(to, subject, message):

    mutt = [
            'mutt',
            '-s',
            subject,
            '-e', 'set copy=no',
            '-e', 'set realname=UNSWtalk',
            '--', to
    ]

    subprocess.run(
            mutt,
            input = message.encode('utf8'),
            stderr = subprocess.PIPE,
            stdout = subprocess.PIPE,
    )

def EmailSender(arg):
    if arg['type'] == 'Friend_request':
        # to_addr = ['lll109512@outlook.com']
        data = arg['data']
        to_addr = [data['user_info']['email']]

        mail_msg = f"""
        UNSWtalk
        You just receive a new friend request of {data['sender_zid']}
        Click to accept this request
        {data['maddr']}
        """
        to = to_addr[0]
        subject = f"New firend request"

    elif arg['type'] == 'Pass_recover':
        data = arg['data']

        to_addr = [data['email']]

        mail_msg = f"""
        UNSWtalk
        Dear {data['zid']},
        This is the new password of your account.
        Change your password as soon as possible.
        Password: {data['new_pass']}
        """
        to = to_addr[0]
        subject = f"Password recover"

    elif arg['type'] == 'Notifications':
        data = arg['data']
        to_addr = [data['email']]
        if DB.GetSuspend(data['zid']) == 'T':
            return
        mail_msg = f"""
        UNSWtalk
        Dear {data['zid']},
        A new {data['rtype']} mentioned you .
        Click to view this {data['rtype']}
        {data['addr']}
        """

        to = to_addr[0]

        subject = f"A new {data['rtype']} mentioned you"

    elif arg['type'] == 'Signup':
        data = arg['data']
        to_addr = [data['email']]

        mail_msg = f"""
        UNSWtalk
        Dear {data['zid']},
        Thank you for signing up UNSWtalk.
        This email is use to verify your email address.
        Click to finish your signup
        {data['addr']}
        """

        to = to_addr[0]

        subject = f"Final step to sign up"

    else:
        print("Error in email type")
        return


    try:
        send_email(to, subject, mail_msg)
    except Exception as e:
        print(e)
        raise e


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_time():
    return time.ctime()

def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'login' in session and session['login']:
            return f(*args, **kwargs)
        else:
            flash("You need to login first")
            return redirect(url_for('main'))
    return wrap

def escape_message(post_comment_reply_dict,limited=None,translate_zid_into_link=True,translate_link_into_link=True):
    for post in post_comment_reply_dict:
        if post['message']:
            post['message'] = " ".join(post['message'].split()[:limited])
            message_list = post['message'].split("\\n")
            new_message_list = []
            for sub_message in message_list:
                zid_list = list(set(re.findall(r'z\d{7}',sub_message)))
                link_list = list(set(re.findall(r"[a-zA-z]+://[^\s]*",sub_message)))
                new_message = sub_message
                if translate_link_into_link:
                    for link in link_list:
                        new_message = new_message.replace(link,f'<a href="{link}">{link}</a>')

                for zid in zid_list:
                    full_name = DB.GetUserInfo(zid)['full_name']
                    if translate_zid_into_link:
                        new_message = new_message.replace(zid,f'<a href="{url_for("user_info")}{zid}">{full_name}</a>')
                    else:
                        new_message = new_message.replace(zid,f'{full_name}')
                new_message_list.append(new_message)
            post['message'] = "<br />".join(new_message_list)

    return post_comment_reply_dict

def scan_zid(post_comment_reply_message):
    zid_list = list(set(re.findall(r'z\d{7}',post_comment_reply_message)))
    return zid_list

def token_generator(size=8, chars=string.ascii_letters + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def process_raw_message(message):
    return message.replace("\r\n","\\n")

def Compute_suggest_friends(zid):
    result = []
    existed_friend = DB.GetFriendsList(zid)
    user_info = DB.GetUserInfo(zid)
    for friend in DB.GetAllUser():
        if friend in existed_friend or friend == session['zid']:
            continue
        target_info = DB.GetUserInfo(friend)
        sorce = (len(set(user_info['courses'])&set(target_info['courses'])))/len(set(user_info['courses']).union(set(target_info['courses'])))
        sorce += (len(set(user_info['friends'])&set(target_info['friends'])))/len(set(user_info['friends']).union(set(target_info['friends'])))
        result.append([sorce,friend])
    return result


@app.route("/", methods=['GET'])
def main():
    try:
        if 'login' in session and session['login']:
            friends_list = DB.GetFriendsList(session['zid'])
            friends_list = list(filter(lambda x:DB.GetSuspend(x) == 'F', friends_list))
            friends_info = DB.GetFriendsInfoList(friends_list)

            My_Post_list = DB.SearchPostsByfrom(session['zid'],5)
            My_Post_list = escape_message(My_Post_list, limited=100,translate_zid_into_link=False,translate_link_into_link=False)

            Friends_post_list = []
            for friend_zid in friends_list:
                Friends_post_list.extend(DB.SearchPostsByfrom(friend_zid,2))
            Friends_post_list.sort(key = lambda x:x['id'],reverse=True)
            Friends_post_list = Friends_post_list[:5]
            Friends_post_list = escape_message(Friends_post_list, limited=100,translate_zid_into_link=False,translate_link_into_link=False)

            related_posts = DB.SearchPostsMentioned(session['zid'])
            related_posts.sort(key = lambda x:x['id'],reverse=True)
            related_posts = related_posts[:5]
            related_posts = escape_message(related_posts, limited=100,translate_zid_into_link=False,translate_link_into_link=False)

            return render_template("main_default.html",friends_list=friends_info,
                    My_Post_list=My_Post_list,Friends_post_list=Friends_post_list,
                    Related_post_list = related_posts)
        else:
            return render_template("main.html")
    except Exception as e:
        raise e
        return render_template("main.html")

@app.route("/search_result/", methods=['GET','POST'])
@login_required
def searchresult():
    try:
        if request.method == 'POST':
            message = request.form['smessage']
            session['search_message'] = message
            post_pagination_num = 1
            frnd_pagination_num = 1
        else:
            post_pagination_num = int(request.args['ppage'])
            frnd_pagination_num = int(request.args['fpage'])
            message = session['search_message']

        post_total_page = math.ceil(DB.SearchPostsByMessageGetTotalNum(message)/page_size)
        post_dict = DB.SearchPostsByMessage(message, Pagination=post_pagination_num)
        post_dict = escape_message(post_dict, limited=100,translate_link_into_link=False,translate_zid_into_link=False)

        friends_list = DB.SearchUserNameHas(message, Pagination=frnd_pagination_num)
        friends_list = list(filter(lambda x:DB.GetSuspend(x['zid']) == 'F', friends_list))
        frnd_total_page = math.ceil(DB.SearchUserNameHasTotalNum(message)/page_size)
        return render_template("search_result.html",Result_post=post_dict, friends_list=friends_list,
                post_pagination_num=post_pagination_num,post_total_page=post_total_page,frnd_total_page=frnd_total_page,
                frnd_pagination_num=frnd_pagination_num)

    except Exception as e:
        raise e
        return redirect(url_for('main'))



@app.route("/log_in_out/", methods=['GET', 'POST'])
def log_in_out_function():
    try:
        if request.method == 'POST':
            attempted_zid = request.form['zid']
            attempted_password = request.form['password']
            if DB.CheckPass(attempted_zid, attempted_password):
                session['zid'] = attempted_zid
                session['login'] = True
                if DB.GetSuspend(attempted_zid) == 'F':
                    session['suspend'] = False
                else:
                    session['suspend'] = True
                session['privacy'] = DB.GetPrivacyLevel(attempted_zid)
            else:
                flash("Wrong zid or password.")
        elif request.method == 'GET':
            if 'logout' in request.args and request.args['logout']:
                session.clear()
                flash("logout successfully!", category='message')
        return redirect(url_for('main'))
    except Exception as e:
        raise e
        return redirect(url_for('main'))



@app.route("/sign_up/", methods=['GET', 'POST'])
@app.route("/sign_up/<string:token>/", methods=['GET'])
def sign_up(token=None):
    try:
        if not token:
            Form = register_form(request.form)
            if request.method == 'GET':
                return render_template("sign_up.html")
            elif request.method == 'POST' and Form.validate():
                if not DB.UserIsExist(Form.zid.data):
                    jsons = json.dumps({'zid': Form.zid.data, 'password': Form.password.data, 'home_suburb': Form.suburb.data,
                                   'courses':Form.courses.data.split(','), 'full_name': Form.fullname.data, 'birthday': Form.birthday.data,
                                   'email': Form.mail.data, 'program': Form.program.data, 'friends': [] ,
                                   'home_longitude': Form.longitude.data, 'home_latitude': Form.latitude.data,'img':app.config['DEFAULT_USER_IMG']})
                    token = token_generator(10)
                    DB.InsertToken(token, 'signup', jsons)
                    addr = request.url_root + f"sign_up/{token}/"
                    email = Form.mail.data

                    if Debug:
                        email = 'lll109512@outlook.com'
                    EmailSender({'type':'Signup','data':{'zid':Form.zid.data,'addr':addr,'email':email}})
                    # EventQueue.put({'type':'Signup','data':{'zid':Form.zid.data,'addr':addr,'email':email}})
                    flash("Please check your email to finish last step.")
                    return redirect(url_for('sign_up'))
                else:
                    flash("User exist! Please check your zid.")
                    return redirect(url_for('sign_up'))
            else:
                flash("Unvalidate information, check again.")
                return render_template("sign_up.html")
        else:
            Jsons = DB.GetJsonByToken(token, 'signup')
            if Jsons:
                user_info = json.loads(Jsons)
                zid = user_info['zid']
                DB.DeleteTokenByToken(token, 'signup')
                if not DB.UserIsExist(zid):
                    flash("sign up successfully")
                    session['zid'] = zid
                    session['login'] = True
                    session['suspend'] = False
                    session['privacy'] = '0'
                    DB.InsertUser(user_info)
                    return redirect(url_for('main'))
                else:
                    flash("User exist!")
                    return redirect(url_for('main'))
            else:
                flash("You need to sign up first!")
                return redirect(url_for('sign_up'))


    except Exception as e:
        raise e
        return render_template("sign_up.html")


@app.route("/user_info/", methods=['GET'])
@app.route("/user_info/<string:zzid>/", methods=['GET'])
@login_required
def user_info(zzid):
    try:
        session['viewing_user_info_zid'] = zzid
        user_info = DB.GetUserInfo(zzid)
        profile = process_raw_message(DB.GetProfileText(zzid))
        profile = escape_message([{'message':profile}], translate_zid_into_link=False)[0]['message']
        privacy_level = DB.GetPrivacyLevel(zzid)
        if DB.GetSuspend(zzid) == 'T' and zzid != session['zid']:
            flash('This account has been suspended, you can not view this people info.')
            return redirect(url_for('main'))
        else:
            return render_template("user_info.html",user_info = user_info,profile = profile,privacy_level = privacy_level)
    except Exception as e:
        raise e
        return render_template("user_info.html")

@app.route("/post/", methods=['GET'])
@app.route("/post/<int:pid>/", methods=['GET'])
@login_required
def post(pid):
    try:
        session['viewing_post'] = pid
        post = DB.SearchPostsByID(pid)
        post = escape_message([post])[0]
        if 'page' in request.args:
            pagination_num = int(request.args['page'])
        else:
            pagination_num = 1
        comments = DB.SearchCommentByPostID(pid)
        total_page = math.ceil(len(comments)/page_size)
        comments = comments[(pagination_num-1)*page_size:pagination_num*page_size]
        crl = []

        for comment in comments:
            comments_reply_dict = {}
            cid = comment['id']
            reply = DB.SearchReplyByCommentID(cid)
            comment = escape_message([comment])[0]
            comments_reply_dict['comment'] = comment
            comments_reply_dict['reply'] = escape_message(reply)
            crl.append(comments_reply_dict)

        User_img_path = DB.GetAllUserImg()
        return render_template("post.html",mpost=post,crl=crl,total_page=total_page,
        pagination_num=pagination_num,User_img_path=User_img_path)
    except Exception as e:
        raise e
        return redirect(url_for('main'))

@app.route("/reply_comment/", methods=['POST'])
@login_required
def reply_comment():
    try:
        message = process_raw_message(request.form['message'])
        cid = request.form['reply_comment_id']
        ctime = get_time()
        DB.InsertReply({'from':session['zid'],'time':ctime,'message':message,'comment_ID':cid})

        zid_list = scan_zid(request.form['message'])
        addr = request.url_root + f"post/{session['viewing_post']}"
        for zid in zid_list:
            if zid != session['zid']:
                info = DB.GetUserInfo(zid)
                if Debug:
                    info['email'] = 'lll109512@outlook.com'
                # EventQueue.put({'type':'Notifications','data':{'email':info['email'],'rtype':'Reply','zid':info['zid'],'addr':addr}})
                EmailSender({'type':'Notifications','data':{'email':info['email'],'rtype':'Reply','zid':info['zid'],'addr':addr}})
        flash('Reply successfully!')
        return redirect(url_for('post')+str(session['viewing_post']))
    except Exception as e:
        raise e
        if session['viewing_post']:
            return redirect(url_for('post')+str(session['viewing_post']))
        else:
            return redirect(url_for('main'))

@app.route("/delete_comment/", methods=['POST'])
@login_required
def delete_comment():
    try:
        cid = request.form['Delete_comment']
        DB.DeleteComment(cid)
        flash('Delete Comment successfully!')
        return redirect(url_for('post')+str(session['viewing_post']))
    except Exception as e:
        raise e
        if session['viewing_post']:
            return redirect(url_for('post')+str(session['viewing_post']))
        else:
            return redirect(url_for('main'))

@app.route("/reply_post/", methods=['POST'])
@login_required
def reply_post():
    try:
        parsed_message = process_raw_message(request.form['message'])
        DB.InsertComment({'from':session['zid'],
                        'time':get_time(),
                        'message':parsed_message,
                        'post_ID':session['viewing_post']})

        zid_list = scan_zid(request.form['message'])
        addr = request.url_root + f"post/{session['viewing_post']}"
        for zid in zid_list:
            if zid != session['zid']:
                info = DB.GetUserInfo(zid)
                if Debug:
                    info['email'] = 'lll109512@outlook.com'
                # EventQueue.put({'type':'Notifications','data':{'email':info['email'],'rtype':'Comment','zid':info['zid'],'addr':addr}})
                EmailSender({'type':'Notifications','data':{'email':info['email'],'rtype':'Comment','zid':info['zid'],'addr':addr}})
        flash('Comment successfully!')
        return redirect(url_for('post')+str(session['viewing_post']))
    except Exception as e:
        raise e
        if session['viewing_post']:
            return redirect(url_for('post')+str(session['viewing_post']))
        else:
            return redirect(url_for('main'))

@app.route("/delete_post/", methods=['POST'])
@login_required
def delete_post():
    try:
        DB.DeletePost(session['viewing_post'])
        flash('Delete post successfully!')
        return redirect(url_for('main'))
    except Exception as e:
        raise e
        return redirect(url_for('main'))

@app.route("/delete_reply/", methods=['POST'])
@login_required
def delete_reply():
    try:
        DB.DeleteReply(request.form['Delete_reply'])
        flash('Delete reply successfully!')
        return redirect(url_for('post')+str(session['viewing_post']))
    except Exception as e:
        raise e
        if session['viewing_post']:
            return redirect(url_for('post')+str(session['viewing_post']))
        else:
            return redirect(url_for('main'))

@app.route("/new_post/", methods=['GET','POST'])
@login_required
def new_post():
    try:
        if request.method == 'GET':
            return render_template('new_post.html')
        else:
            parsed_message = process_raw_message(request.form['message'])

            pid = DB.InsertPost({'from':session['zid'],
                            'latitude':request.form['latitude'],
                            'longitude':request.form['longitude'],
                            'time':get_time(),
                            'message':parsed_message})


            zid_list = scan_zid(request.form['message'])
            addr = request.url_root + f'post/{pid}'
            for zid in zid_list:
                if zid != session['zid']:
                    info = DB.GetUserInfo(zid)
                    if Debug:
                        info['email'] = 'lll109512@outlook.com'
                    # EventQueue.put({'type':'Notifications','data':{'email':info['email'],'rtype':'Post','zid':info['zid'],'addr':addr}})
                    EmailSender({'type':'Notifications','data':{'email':info['email'],'rtype':'Post','zid':info['zid'],'addr':addr}})
            flash("Post successfully!")
            return redirect(url_for('post')+str(pid))
    except Exception as e:
        raise e
        return redirect(url_for('main'))


@app.route("/friend_ops/", methods=['POST'])
@login_required
def friend_ops():
    try:
        ops = request.form['friend']
        if ops == 'unfriend':
            MFL = DB.GetFriendsList(session['zid'])
            MFL.remove(session['viewing_user_info_zid'])
            FFL = DB.GetFriendsList(session['viewing_user_info_zid'])
            FFL.remove(session['zid'])
            DB.UpdateFriendList(session['zid'], MFL)
            DB.UpdateFriendList(session['viewing_user_info_zid'], FFL)
            flash('unfriend successfully')
        else:
            info = DB.GetUserInfo(session['viewing_user_info_zid'])
            comwebaddr = request.url_root + f"request_process?sender_zid={session['zid']}&receiver_zid={session['viewing_user_info_zid']}"
            arg = {'user_info':info,'sender_zid':session['zid'],'maddr':comwebaddr}
            if Debug:
                arg['user_info']['email'] = 'lll109512@outlook.com'
            combdata = {'type':'Friend_request','data':arg}

            EmailSender(combdata)
            flash('Send request successfully')
        return redirect(url_for('user_info') + session['viewing_user_info_zid'])
    except Exception as e:
        raise e
        return redirect(url_for('user_info') + session['viewing_user_info_zid'])


@app.route("/request_process/", methods=['GET','POST'])
def friend_request_process():
    try:
        if request.method == 'GET':
            sender = request.args['sender_zid']
            receiver = request.args['receiver_zid']
            info = DB.GetUserInfo(sender)
            return render_template('request_page.html',user_info = info,receiver = receiver)
        else:
            sender = request.form['sender']
            receiver = request.form['receiver']
            if 'accept' in request.form:
                sender_friend_list = list(set(DB.GetFriendsList(sender) + [receiver]))
                DB.UpdateFriendList(sender, sender_friend_list)
                receiver_friend_list = list(set(DB.GetFriendsList(receiver) + [sender]))
                DB.UpdateFriendList(receiver, receiver_friend_list)
                flash("Request has been accepted")
            else:
                flash("Request has been rejected")
            return redirect(url_for('main'))
    except Exception as e:
        raise e
        return redirect(url_for('main'))

@app.route("/forget_pass/", methods=['GET','POST'])
def forget_pass():
    try:
        if request.method == 'GET':
            return render_template('forget_pass.html')
        else:
            Form = forget_pass_form(request.form)
            if Form.validate():
                email = Form.mail.data
                zid = Form.zid.data
                if DB.UserIsExist(zid):
                    if DB.GetUserInfo(zid)['email'] == email:
                        new_pass = token_generator()
                        DB.UpdatePass(zid,new_pass)
                        combdata = {'type':'Pass_recover','data':{'zid':zid,'new_pass':new_pass,'email':email}}
                        combdata['data']['email'] = 'lll109512@outlook.com'
                        # EventQueue.put(combdata)
                        EmailSender(combdata)
                        flash('Check your email, the new pass have been sent to you. Change your pass as soon as possible and make sure not forgot it again.')
                        return redirect(url_for('main'))
                    else:
                        flash('Email address error, check your zid or email address.')
                        return render_template('forget_pass.html')
                else:
                    flash('zid doesn\'t exist!')
                    return render_template('forget_pass.html')
            else:
                flash('Invalid Email or zid')
                return render_template('forget_pass.html')
    except Exception as e:
        raise e
        return redirect(url_for('main'))

@app.route("/edit_user_info/", methods=['GET','POST'])
@login_required
def edit_user_info():
    try:
        if request.method == 'GET':
            user_info = DB.GetUserInfo(session['zid'])
            user_info['courses'] = ','.join(user_info['courses'])
            profile = DB.GetProfileText(session['zid'])
            return render_template('edit_user_info.html',user_info=user_info,profile=profile)
        else:
            Form = edit_user_info_form(request.form)
            if Form.validate():
                user_info = DB.GetUserInfo(session['zid'])
                DB.UpdateUserInfo(session['zid'],{'full_name':Form.fullname.data,'email':Form.mail.data,'home_suburb':Form.suburb.data,
                                    'home_latitude':Form.latitude.data,'home_longitude':Form.longitude.data,'program':Form.program.data,
                                    'courses':Form.courses.data.split(','),'birthday':Form.birthday.data})
                DB.UpdateProfileText(session['zid'],Form.profile.data)
                flash('Edit successfully')
                return redirect('edit_user_info')
            else:
                flash("New info get wrong format, please check it again.")
                return redirect('edit_user_info')

    except Exception as e:
        raise e
        return redirect(url_for('main'))

@app.route("/upload_img/", methods=['POST'])
@login_required
def upload_img():
    try:
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect('edit_user_info')
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            suffix = filename.split('.')[1]
            filename = f"{session['zid']}.{suffix}"
            former_img_path = DB.GetUserInfo(session['zid'])['img']

            if app.config['DEFAULT_USER_IMG'] != former_img_path:
                os.remove(os.getcwd()+'/static/'+former_img_path)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            new_path = f"img/userphotos/{filename}"
            DB.ChangeProfileImg(session['zid'], new_path)
            flash('Change profile img successfully')
            return redirect('edit_user_info')

    except Exception as e:
        raise e
        return redirect(url_for('main'))

@app.route("/del_profile_img/", methods=['GET'])
@login_required
def del_profile_img():
    try:
        if DB.GetUserInfo(session['zid'])['img'] == app.config['DEFAULT_USER_IMG']:
            flash('You are using default img.')
        else:
            DB.ChangeProfileImg(session['zid'], app.config['DEFAULT_USER_IMG'])
            flash('Delete your profile img successfully')
        return redirect('edit_user_info')
    except Exception as e:
        raise e
        return redirect(url_for('main'))

@app.route("/friend_suggestion/", methods=['GET'])
@login_required
def friend_suggestion():
    try:
        sorce_list = Compute_suggest_friends(session['zid'])
        sorce_list = list(filter(lambda x:x[0]>SIMILARITY_T, sorce_list))
        sorce_list.sort(key = lambda x:x[0],reverse=True)
        sorce_list = sorce_list[:15]
        info_dict = {}
        if Debug:
            print(sorce_list)
        for sorce in sorce_list:
            info_dict[sorce[1]] = DB.GetUserInfo(sorce[1])
        return render_template('friend_suggestion.html',sorce_list=sorce_list,info_dict = info_dict)
    except Exception as e:
        raise e
        return redirect(url_for('main'))

@app.route("/suspend/", methods=['POST'])
@login_required
def suspend():
    try:
        if request.form['suspend'] == 'suspend':
            session['suspend'] = True
            DB.SetSuspendState(session['zid'], 'T')
            flash('Suspend successfully')
        else:
            session['suspend'] = False
            DB.SetSuspendState(session['zid'], 'F')
            flash('Unsuspend successfully')
        return redirect(url_for('main'))
    except Exception as e:
        raise e
        return redirect(url_for('main'))

@app.route("/delete_account/", methods=['POST'])
@login_required
def delete_account():
    try:
        if request.form['delete_account'] == 'ORZ':
            img = DB.GetUserInfo(session['zid'])['img']
            if not DB.GetUserInfo(session['zid'])['img'] == app.config['DEFAULT_USER_IMG']:
                os.remove(os.getcwd()+'/static/'+img)
                # os.remove(os.getcwd()+url_for('static',filename=img))
            Friend_list = DB.GetFriendsList(session['zid'])
            for friend in Friend_list:
                other = DB.GetFriendsList(friend)
                other.remove(session['zid'])
                DB.UpdateFriendList(friend, other)
            for post in DB.SearchPostsByfrom(session['zid']):
                DB.DeletePost(post['id'])
            for comment in DB.SearchCommentByfrom(session['zid']):
                DB.DeleteComment(comment['id'])
            for reply in DB.SearchReplyByfrom(session['zid']):
                DB.DeleteReply(reply['id'])
            DB.DeleteUser(session['zid'])

            session.clear()
            flash('Account delete successfully!')
        return redirect(url_for('main'))
    except Exception as e:
        raise e
        return redirect(url_for('main'))

@app.route("/set_privacy/", methods=['POST'])
@login_required
def set_privacy():
    try:
        DB.SetPrivacyLevel(session['zid'], request.form['Privacyoption'])
        session['privacy'] = request.form['Privacyoption']
        flash('Change privacy successfully')
        return redirect(url_for('main'))
    except Exception as e:
        raise e
        return redirect(url_for('main'))

@app.route("/change_password/", methods=['POST'])
@login_required
def change_password():
    try:
        Form = new_pass_form(request.form)
        if Form.validate():
            DB.UpdatePass(session['zid'], Form.password.data)
            flash('Change successfully')
        else:
            flash('Unvalidate password')
        return redirect(url_for('main'))
    except Exception as e:
        raise e
        return redirect(url_for('main'))

# FriendRequest_t = threading.Thread(target = EmailSender,args = (EventQueue,))
# FriendRequest_t.start()

if __name__ == '__main__':
    app.secret_key = os.urandom(12)
    app.run(debug=True)
