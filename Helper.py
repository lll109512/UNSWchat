#!/usr/bin/python3.6
import glob
import os
import sqlite3
import hashlib
import shutil



class Filehelper:
    def __init__(self, dir,df_img,img_dir):
        assert os.path.exists(dir),"Directory not exists!"
        self.home_dir = dir
        self.User_list = os.listdir(self.home_dir)
        self.default_img = df_img
        self.img_dir = img_dir

    def IsExist(self, zid):
        """
        Tested!
        Type:
        zid:String
        """
        if zid not in self.User_list:
            return False
        else:
            return True

    def UserImg(self,zid):
        """
        Tested!
        Type:
        zid:String
        """
        if self.IsExist(zid):
            if os.path.exists(f"{self.home_dir}/{zid}/img.jpg"):
                return f"{self.home_dir}/{zid}/img.jpg"
            else:
                return None
        else:
            return None

    def CopyImg(self,sourceimg,targetimg):
        shutil.copy(sourceimg,  sourceimg)
        pass

    def UserInfo(self, zid):
        """
        Tested!
        Type:
        zid:String

        return dict
        Info_dict = {'zid': None, 'password': None, 'home_suburb': None,
                    'courses': [], 'full_name': None, 'birthday': None,
                    'email': None, 'program': None, 'friends': [],
                    'home_longitude': None,'home_latitude': None}
        """
        if self.IsExist(zid):
            Info_dict = {'zid': None, 'password': None, 'home_suburb': None,
                        'courses': [], 'full_name': None, 'birthday': None,
                        'email': None, 'program': None, 'friends': [],
                        'home_longitude': None,'home_latitude': None}
            with open(f"{self.home_dir}/{zid}/student.txt", 'r') as F:
                for line in F:
                    trimed = line.strip()
                    key,value = trimed.split(":")
                    value = value.strip()
                    if key in ['courses','friends']:
                        value = value.strip("()").split(",")
                    Info_dict[key] = value
            if self.UserImg(zid) is not None:
                shutil.copy(self.UserImg(zid),f"static/{self.img_dir}/{Info_dict['zid']}.jpg")
                Info_dict['img'] = f"{self.img_dir}/{Info_dict['zid']}.jpg"
            else:
                Info_dict['img'] = f"{self.img_dir}/{self.default_img}"
            return Info_dict
        else:
            return None


    def LoadPosts(self):
        """
        Tested!
        return dict
        {
        4 {'post': 'resource/dataset-small/z5197433/4.txt', 'comments': ['0', '1'], 'reply': {'0': ['0'], '1': ['0', '1']}} * # of posts
        }
        """
        result = {}
        for userid in self.User_list:
            file_list = set(os.listdir(f"{self.home_dir}/{userid}")) - set(['student.txt','img.jpg'])
            file_list = sorted(list(file_list))
            file_des_dict = {}
            for entirepostname in file_list:
                postname = entirepostname.replace(".txt","")
                sp = postname.split("-")
                if sp[0] not in file_des_dict.keys():
                    file_des_dict[sp[0]] = {'post':None,'comments':[],'reply':{}}
                if len(sp) == 1:
                    file_des_dict[sp[0]]['post'] = f"{self.home_dir}/{userid}/{entirepostname}"
                elif len(sp) == 2:
                    file_des_dict[sp[0]]['comments'].append(sp[1])
                else:
                    if sp[1] not in file_des_dict[sp[0]]['reply'].keys():
                        file_des_dict[sp[0]]['reply'][sp[1]] = []
                    file_des_dict[sp[0]]['reply'][sp[1]].append(sp[2])
            result[userid] = file_des_dict
        return result

    def ReadPost(self,post_file):
        """
        Tested!
        Type:
        post_file : String
        post file path

        return post_dict
        post_dict:dict {from:String,
                        latitude:String,
                        longitude:String,
                        time:String,
                        message:string}
        """
        post_dict = {'from':None,'latitude':None,'longitude':None,'time':None,'message':None}
        with open(post_file, 'r') as F:
            for line in F:
                line = line.strip()
                try:
                    item, value = line.split(":",maxsplit=1)
                    post_dict[item] = value.strip()
                except:
                    post_dict[item] += line
        return post_dict

    def ReadCommentOrReply(self,file_path):
        """
        Tested!
        Type:
        file_path : String
        file path

        return dict
        result_dict:dict {from:String,
                        time:String,
                        message:string}
        """
        result_dict = {'from':None,'time':None,'message':None}
        with open(file_path, 'r') as F:
            for line in F:
                line = line.strip()
                try:
                    item, value = line.split(":",maxsplit=1)
                    result_dict[item] = value.strip()
                except:
                    result_dict[item] += line
        return result_dict

    def LoadPostsInDB(self,DBhelper):
        """
        Tested!
        Type:
        Instance of DBhelper class
        """
        post_dict = self.LoadPosts()
        for file_des_dict in post_dict.values():
            for post in file_des_dict.keys():
                post_dict = self.ReadPost(file_des_dict[post]['post'])
                post_rowid = DBhelper.InsertPost(post_dict)
                for comment in file_des_dict[post]['comments']:
                    comment_file_path = file_des_dict[post]['post'].replace(".txt","") + f"-{comment}.txt"
                    comment_dict = self.ReadCommentOrReply(comment_file_path)
                    comment_dict['post_ID'] = post_rowid
                    comment_rowid = DBhelper.InsertComment(comment_dict)
                    if comment in file_des_dict[post]['reply'].keys():
                        for reply in file_des_dict[post]['reply'][comment]:
                            reply_file_path = file_des_dict[post]['post'].replace(".txt","") + f"-{comment}-{reply}.txt"
                            reply_dict = self.ReadCommentOrReply(reply_file_path)
                            reply_dict['comment_ID'] = comment_rowid
                            DBhelper.InsertReply(reply_dict)




class DBhelper:
    def __init__(self, DB, encrypt_key,page_size = 10):
        self.DBname = DB
        self.Key = encrypt_key.encode('utf-8')
        self.page_size = page_size

    def CreateDB(self,sql_script):
        """
        Tested!
        Type:
        Info_dict : sql_script filename
        """
        with open(sql_script,'r') as F:
            script = F.read()
        with sqlite3.connect(self.DBname) as conn:
            c = conn.cursor()
            c.executescript(script)
            conn.commit()

    def InsertUser(self,Info_dict):
        """
        Tested!
        Type:
        Info_dict : dict
        Info_dict = {'zid': None, 'password': None, 'home_suburb': None,
                    'courses': [], 'full_name': None, 'birthday': None,
                    'email': None, 'program': None, 'friends': [],
                    'home_longitude': None,'home_latitude': None}
        """
        Item = []
        Values = []
        for key in Info_dict.keys():
            if key == 'password':
                continue
            v = Info_dict[key]
            if key in ['courses','friends']:
                v = ",".join(v)
            Item.append(key.upper())
            Values.append(v)
        parameter_palce = "("+ ','.join(['?']*len(Values)) +")"
        I = "("+ ','.join(Item) +")"
        with sqlite3.connect(self.DBname) as conn:
            c = conn.cursor()
            c.execute(f"insert into user_info {I} values {parameter_palce}",Values)
            c.execute(f"insert into pass_info (ZID,PASS) values (?,?)",(Info_dict['zid'],self.Encrypt(Info_dict['password'])))
            conn.commit()
        self.InitialProfileText(Info_dict['zid'])
        self.InitialAcountSetting(Info_dict['zid'])

    def DeleteUser(self,zid):
        """
        Tested!
        Type:
        post_ID:String
        """
        with sqlite3.connect(self.DBname) as conn:
            c = conn.cursor()
            c.execute("delete from user_info where ZID = (?)",[zid])
            c.execute("delete from pass_info where ZID = (?)",[zid])
            c.execute("delete from profile where ZID = (?)",[zid])
            c.execute("delete from account_setting where ZID = (?)",[zid])
            conn.commit()



    def Encrypt(self,passw):
        """
        Tested!
        Type:
        passw:String

        Return encrypted password (String)
        """
        m = hashlib.md5(self.Key)
        m.update(passw.encode('utf-8'))
        return m.hexdigest()


    def UserIsExist(self,zid):
        """
        Tested!
        Type:
        zid:String

        Return Boolean
        """
        with sqlite3.connect(self.DBname) as conn:
            c = conn.cursor()
            c.execute(f"select ZID from pass_info where ZID = (?)",[zid])
            if c.fetchone():
                return True
            else:
                return False

    def CheckPass(self,zid,passw):
        """
        Tested!
        Type:
        passw:String
        zid:String

        Return Boolean
        """
        if self.UserIsExist(zid):
            target_passw = self.Encrypt(passw)
            with sqlite3.connect(self.DBname) as conn:
                c = conn.cursor()
                c.execute(f"select PASS from pass_info where ZID = (?)",[zid])
                if c.fetchone()[0] == target_passw:
                    return True
                else:
                    return False
        else:
            return False

    def SearchName(self,name):
        """
        Tested!
        Type:
        name:String

        Return List of dict
        [
        {'zid':String,'full_name':String,'img':String} * #result
        ]
        """
        result = []
        with sqlite3.connect(self.DBname) as conn:
            c = conn.cursor()
            c.execute(f"select ZID,FULL_NAME,IMG from user_info where FULL_NAME like (?)",[f"%{name}%"])
            for line in c.fetchall():
                result.append({'zid':line[0],'full_name':line[1],'img':line[2]})
        return result

    def GetFriendsList(self,zid):
        """
        Tested!
        Type:
        zid:String

        Return List of zid
        """
        with sqlite3.connect(self.DBname) as conn:
            c = conn.cursor()
            c.execute(f"select FRIENDS from user_info where ZID = (?)",[zid])
            result = c.fetchone()
            if result:
                return result[0].split(',')
            else:
                return []

    def ReorganizeFriendList(self):
        """
        Only set friend shared each other
        """
        with sqlite3.connect(self.DBname) as conn:
            c = conn.cursor()
            c.execute("select ZID, FRIENDS from user_info")
            user_list = c.fetchall()
            for user, friends in user_list:
                out = set()
                friends = [x.strip() for x in friends.split(",")]
                for friend in friends:
                    c.execute("select FRIENDS from user_info where ZID = (?)",[friend])
                    TFL = c.fetchone()[0]
                    TFL = [x.strip() for x in TFL.split(",")]
                    if user not in TFL:
                        out.add(friend)
                NFL = list(set(friends) - out)
                self.UpdateFriendList(user,NFL)


    def UpdateFriendList(self,zid,New_friend_list):
        """
        input:
        New_friend_list:list of firends zid
        """
        New_friend_list = ','.join(New_friend_list)
        with sqlite3.connect(self.DBname) as conn:
            c = conn.cursor()
            c.execute("update user_info set FRIENDS = (?) where ZID = (?)",[New_friend_list,zid])
            conn.commit()

    def GetAllUserImg(self):
        result = {}
        with sqlite3.connect(self.DBname) as conn:
            c = conn.cursor()
            c.execute("select ZID, IMG from user_info")
            for line in c.fetchall():
                result[line[0]] = line[1]
        return result

    def GetAllUser(self):
        result = []
        with sqlite3.connect(self.DBname) as conn:
            c = conn.cursor()
            c.execute("select ZID from user_info")
            for line in c.fetchall():
                result.append(line[0])
        return result

    def GetFriendsInfoList(self,zid_list):
        """
        Tested!
        Type:
        zid_list:[zid,zid,....]

        Return List of dict
        [
        {'zid':String,'full_name':String,'img':String} * #result
        ]
        """
        result = []
        with sqlite3.connect(self.DBname) as conn:
            c = conn.cursor()
            for zid in zid_list:
                c.execute(f"select ZID,FULL_NAME,IMG from user_info where ZID = (?)",[zid])
                line = c.fetchone()
                if line:
                    result.append({'zid':line[0],'full_name':line[1],'img':line[2]})
        return result

    def SearchUserNameHas(self,subname,Pagination=None):
        """
        Tested!
        Type:
        subname:String

        Return List of zid_dict
        """
        result = []
        with sqlite3.connect(self.DBname) as conn:
            c = conn.cursor()
            if Pagination:
                offset = self.page_size * (Pagination - 1)
                c.execute(f"select ZID,FULL_NAME,IMG from user_info where FULL_NAME like (?) order by ZID LIMIT {self.page_size} OFFSET {offset}",[f"%{subname}%"])
            else:
                c.execute(f"select ZID,FULL_NAME,IMG from user_info where FULL_NAME like (?) order by ZID",[f"%{subname}%"])
            for line in c.fetchall():
                result.append({'zid':line[0],'full_name':line[1],'img':line[2]})
        return result

    def SearchUserNameHasTotalNum(self,subname):
        with sqlite3.connect(self.DBname) as conn:
            c = conn.cursor()
            c.execute(f"select count(*) from user_info where FULL_NAME like (?) order by ZID",[f"%{subname}%"])
            result = c.fetchone()
            if result[0]:
                return int(result[0])
            else:
                return 0

    def GetUserInfo(self,zid):
        """
        Tested!
        Type:
        zid:String

        Return dict
        """
        if self.UserIsExist(zid):
            with sqlite3.connect(self.DBname) as conn:
                Info_dict = {}
                c = conn.cursor()
                c.execute(f"select * from user_info where ZID = (?)",[zid])
                result = c.fetchone()[1:]
                item_list = ['zid','full_name','home_latitude','home_longitude','home_suburb',
                            'program','friends','email','courses','birthday','img']
                for i,item in enumerate(item_list):
                    if item in ['courses','friends']:
                        Info_dict[item] = [x.strip() for x in result[i].split(",")]
                    else:
                        Info_dict[item] = result[i]
                return Info_dict
        else:
            return None


    def InsertPost(self,post_dict):
        """
        Tested!
        Type:
        post_dict:dict {from:String,
                        latitude:String,
                        longitude:String,
                        time:String,
                        message:string}
        Return Post_ID
        """
        with sqlite3.connect(self.DBname) as conn:
            c = conn.cursor()
            c.execute("insert into posts (MESSAGE,'FROM','TIME',LATITUDE,LONGITUDE) values (?,?,?,?,?)",
                        [post_dict['message'],post_dict['from'],post_dict['time'],post_dict['latitude'],post_dict['longitude']])
            conn.commit()
            c.execute("select last_insert_rowid() from posts")
            return c.fetchone()[0]

    def DeletePost(self,post_ID):
        """
        Tested!
        Type:
        post_ID:String
        """
        with sqlite3.connect(self.DBname) as conn:
            c = conn.cursor()
            c.execute("PRAGMA foreign_keys = ON")
            c.execute("delete from posts where ID = (?)",[post_ID])
            conn.commit()

    def SearchPostsByMessage(self,message,Pagination=None):
        """
        Tested!
        Type:
        message:String

        return list of batch dict
        [
        {'id':line[0],'message':line[1],'from':line[2],'time':line[3],
                        'latitude':line[4],'longitude':line[5]}
        ]
        """
        result = []
        with sqlite3.connect(self.DBname) as conn:
            c = conn.cursor()
            if Pagination:
                offset = self.page_size * (Pagination - 1)
                c.execute(f"select * from posts where MESSAGE like (?) ORDER BY ID DESC LIMIT {self.page_size} OFFSET {offset} ",[f"%{message}%"])
            else:
                c.execute(f"select * from posts where MESSAGE like (?) ORDER BY ID DESC",[f"%{message}%"])
            for line in c.fetchall():
                result.append({'id':line[0],'message':line[1],'from':line[2],'time':line[3],
                                'latitude':line[4],'longitude':line[5]})
        return result

    def SearchPostsByMessageGetTotalNum(self,message):
        with sqlite3.connect(self.DBname) as conn:
            c = conn.cursor()
            c.execute(f"select count(*) from posts where MESSAGE like (?)",[f"%{message}%"])
            result = c.fetchone()
            if result[0]:
                return int(result[0])
            else:
                return 0


    def SearchPostsByfrom(self,zid,limited = None):
        """
        Type:
        from:String

        return list of batch dict
        [
        {'id':line[0],'message':line[1],'from':line[2],'time':line[3],
                        'latitude':line[4],'longitude':line[5]}
        ]
        """
        result = []
        with sqlite3.connect(self.DBname) as conn:
            c = conn.cursor()
            if not limited:
                c.execute(f"select * from posts where \"FROM\" = (?) order by ID DESC",[zid])
            else:
                c.execute(f"select * from posts where \"FROM\" = (?) order by ID DESC LIMIT (?)",[zid,limited])
            for line in c.fetchall():
                result.append({'id':line[0],'message':line[1],'from':line[2],'time':line[3],
                                'latitude':line[4],'longitude':line[5]})
        return result

    def SearchPostsByID(self,id):
        """
        Tested!
        Type:
        id:String

        return dict
        [
        {'id':line[0],'message':line[1],'from':line[2],'time':line[3],
                        'latitude':line[4],'longitude':line[5]}
        ]
        """
        with sqlite3.connect(self.DBname) as conn:
            c = conn.cursor()
            c.execute(f"select * from posts where ID = (?)",[id])
            line = c.fetchone()
            result = {'id':line[0],'message':line[1],'from':line[2],'time':line[3],
                                'latitude':line[4],'longitude':line[5]}
        return result


    def ReturnALLPost(self):
        """
        Type:
        message:String

        return list of batch dict
        [
        {'id':line[0],'message':line[1],'from':line[2],'time':line[3],
                        'latitude':line[4],'longitude':line[5]}
        ]
        """
        result = []
        with sqlite3.connect(self.DBname) as conn:
            c = conn.cursor()
            c.execute(f"select * from posts")
            for line in c.fetchall():
                result.append({'id':line[0],'message':line[1],'from':line[2],'time':line[3],
                                'latitude':line[4],'longitude':line[5]})
        return result


    def InsertComment(self,comment_dict):
        """
        Tested!
        Type:
        comment_dict:dict {from:String,
                        time:String,
                        message:string,
                        post_ID:String}
        Return comment_ID
        """
        with sqlite3.connect(self.DBname) as conn:
            c = conn.cursor()
            c.execute("insert into comments (MESSAGE,'FROM','TIME',POSTID) values (?,?,?,?)",
                        [comment_dict['message'],comment_dict['from'],comment_dict['time'],comment_dict['post_ID']])
            conn.commit()
            c.execute("select last_insert_rowid() from comments")
            return c.fetchone()[0]


    def DeleteComment(self,comment_ID):
        """
        Tested!
        Type:
        comment_ID:String
        """
        with sqlite3.connect(self.DBname) as conn:
            c = conn.cursor()
            c.execute("PRAGMA foreign_keys = ON")
            c.execute("delete from comments where ID = (?)",[comment_ID])
            conn.commit()

    def SearchCommentByMessage(self,message):
        """
        Type:
        message:String

        return list of batch dict
        [
        {'id':line[0],'message':line[1],'from':line[2],'time':line[3],'post_ID':line[4]}
        ]
        """
        result = []
        with sqlite3.connect(self.DBname) as conn:
            c = conn.cursor()
            c.execute(f"select * from comments where MESSAGE like (?)",[f"%{message}%"])
            for line in c.fetchall():
                result.append({'id':line[0],'message':line[1],'from':line[2],'time':line[3],'post_ID':line[4]})
        return result

    def SearchCommentByfrom(self,zid):
        """
        Type:
        from:String

        return list of batch dict
        [
        {'id':line[0],'message':line[1],'from':line[2],'time':line[3],'post_ID':line[4]}
        ]
        """
        result = []
        with sqlite3.connect(self.DBname) as conn:
            c = conn.cursor()
            c.execute(f"select * from comments where \"FROM\" = (?)",[zid])
            for line in c.fetchall():
                result.append({'id':line[0],'message':line[1],'from':line[2],'time':line[3],'post_ID':line[4]})
        return result

    def SearchCommentByID(self,id):
        """
        Tested!
        Type:
        id:String

        return dict
        [
        {'id':line[0],'message':line[1],'from':line[2],'time':line[3],'post_ID':line[4]}
        ]
        """
        with sqlite3.connect(self.DBname) as conn:
            c = conn.cursor()
            c.execute(f"select * from comments where ID = (?)",[id])
            line = c.fetchone()
            result = {'id':line[0],'message':line[1],'from':line[2],'time':line[3],'post_ID':line[4]}
        return result

    def SearchCommentByPostID(self,post_id):
        """
        Tested!
        Type:
        id:int

        return dict
        [
        {'id':line[0],'message':line[1],'from':line[2],'time':line[3],'post_ID':line[4]}
        ]
        """
        result = []
        with sqlite3.connect(self.DBname) as conn:
            c = conn.cursor()
            c.execute(f"select * from comments where POSTID = (?)",[post_id])
            for line in c.fetchall():
                result.append({'id':line[0],'message':line[1],'from':line[2],'time':line[3],'post_ID':line[4]})
        return result


    def InsertReply(self,reply_dict):
        """
        Tested!
        Type:
        reply_dict:dict {from:String,
                        time:String,
                        message:string,
                        comment_ID:String}
        """
        with sqlite3.connect(self.DBname) as conn:
            c = conn.cursor()
            c.execute("insert into reply (MESSAGE,'FROM','TIME',COMMENTID) values (?,?,?,?)",
                        [reply_dict['message'],reply_dict['from'],reply_dict['time'],reply_dict['comment_ID']])
            conn.commit()
            c.execute("select last_insert_rowid() from reply")
            return c.fetchone()[0]

    def DeleteReply(self,reply_ID):
        """
        Tested!
        Type:
        reply_ID:String
        """
        with sqlite3.connect(self.DBname) as conn:
            c = conn.cursor()
            c.execute("delete from reply where ID = (?)",[reply_ID])
            conn.commit()

    def SearchReplyByMessage(self,message):
        """
        Type:
        message:String

        return list of batch dict
        [
        {'id':line[0],'message':line[1],'from':line[2],'time':line[3],'comment_ID':line[4]}
        ]
        """
        result = []
        with sqlite3.connect(self.DBname) as conn:
            c = conn.cursor()
            c.execute(f"select * from reply where MESSAGE like (?)",[f"%{message}%"])
            for line in c.fetchall():
                result.append({'id':line[0],'message':line[1],'from':line[2],'time':line[3],'comment_ID':line[4]})
        return result

    def SearchReplyByfrom(self,zid):
        """
        Type:
        from:String

        return list of batch dict
        [
        {'id':line[0],'message':line[1],'from':line[2],'time':line[3],'comment_ID':line[4]}
        ]
        """
        result = []
        with sqlite3.connect(self.DBname) as conn:
            c = conn.cursor()
            c.execute(f"select * from reply where \"FROM\" = (?)",[zid])
            for line in c.fetchall():
                result.append({'id':line[0],'message':line[1],'from':line[2],'time':line[3],'comment_ID':line[4]})
        return result

    def SearchReplyByID(self,id):
        """
        Type:
        id:String

        return dict
        [
        {'id':line[0],'message':line[1],'from':line[2],'time':line[3],'comment_ID':line[4]}
        ]
        """
        with sqlite3.connect(self.DBname) as conn:
            c = conn.cursor()
            c.execute(f"select * from reply where ID = (?)",[id])
            line = c.fetchone()
            result = {'id':line[0],'message':line[1],'from':line[2],'time':line[3],'comment_ID':line[4]}
        return result

    def SearchReplyByCommentID(self,Comment_id):
        """
        Type:
        id:String

        return dict
        [
        {'id':line[0],'message':line[1],'from':line[2],'time':line[3],'comment_ID':line[4]}
        ]
        """
        result = []
        with sqlite3.connect(self.DBname) as conn:
            c = conn.cursor()
            c.execute(f"select * from reply where COMMENTID = (?)",[Comment_id])
            for line in c.fetchall():
                result.append({'id':line[0],'message':line[1],'from':line[2],'time':line[3],'comment_ID':line[4]})
        return result

    def SearchPostsMentioned(self,message):
        reply_list = self.SearchReplyByMessage(message)
        comments_list = self.SearchCommentByMessage(message)
        post_list = self.SearchPostsByMessage(message)

        Relyed_comments_id = [dic['comment_ID'] for dic in self.SearchReplyByMessage(message)]
        mearged_comments_id = Relyed_comments_id + [dic['id'] for dic in comments_list]
        Relyed_comments_id = list(set(Relyed_comments_id))

        post_id = []
        for comment_id in Relyed_comments_id:
            post_id.append(self.SearchCommentByID(comment_id)['post_ID'])

        post_id = post_id + [dic['id'] for dic in post_list]
        post_id = list(set(post_id))

        related_posts = []
        for pid in post_id:
            related_posts.append(self.SearchPostsByID(pid))
        return related_posts


    def UpdatePass(self,zid,passw):
        passw = self.Encrypt(passw)
        with sqlite3.connect(self.DBname) as conn:
            c = conn.cursor()
            c.execute("update pass_info set PASS = (?) where ZID = (?)",[passw,zid])
            conn.commit()

    def ChangeProfileImg(self,zid,img_path):
        with sqlite3.connect(self.DBname) as conn:
            c = conn.cursor()
            c.execute("update user_info set IMG = (?) where ZID = (?)",[img_path,zid])
            conn.commit()

    def UpdateProfileText(self,zid,text):
        with sqlite3.connect(self.DBname) as conn:
            c = conn.cursor()
            c.execute("update profile set PROFILE = (?) where ZID = (?)",[text,zid])
            conn.commit()

    def InitialProfileText(self,zid):
        with sqlite3.connect(self.DBname) as conn:
            c = conn.cursor()
            c.execute("insert into profile (ZID,PROFILE) values (?,?)",[zid,''])
            conn.commit()

    def GetProfileText(self,zid):
        with sqlite3.connect(self.DBname) as conn:
            c = conn.cursor()
            c.execute("select PROFILE from profile where ZID = (?)",[zid])
            result = c.fetchone()
            if result[0]:
                return result[0]
            else:
                return ''

    def InsertToken(self,token,Type,json):
        with sqlite3.connect(self.DBname) as conn:
            c = conn.cursor()
            c.execute("insert into ready_table (TOKEN,TYPE,JSON) values (?,?,?)",[token,Type,json])
            conn.commit()

    def GetJsonByToken(self,Token,Type):
        with sqlite3.connect(self.DBname) as conn:
            c = conn.cursor()
            c.execute("select JSON from ready_table where TOKEN = (?) and TYPE = (?)",[Token,Type])
            result = c.fetchone()
            if result:
                return result[0]
            else:
                return None
    def DeleteTokenByToken(self,Token,Type):
        with sqlite3.connect(self.DBname) as conn:
            c = conn.cursor()
            c.execute("delete from ready_table where TOKEN = (?) and TYPE = (?)",[Token,Type])
            conn.commit()


    def InitialAcountSetting(self,zid):
        with sqlite3.connect(self.DBname) as conn:
            c = conn.cursor()
            c.execute("insert into account_setting (ZID,SUSPEND,PRIVACY_LEVEL) values (?,?,?)",[zid,'F','0'])
            conn.commit()

    def GetSuspend(self,zid):
        with sqlite3.connect(self.DBname) as conn:
            c = conn.cursor()
            c.execute(f"select SUSPEND from account_setting where ZID = (?)",[zid])
            result = c.fetchone()
            if result:
                return result[0]
            else:
                return 'F'

    def SetSuspendState(self,zid,state):
        with sqlite3.connect(self.DBname) as conn:
            c = conn.cursor()
            c.execute("update account_setting set SUSPEND = (?) where ZID = (?)",[state,zid])
            conn.commit()

    def GetPrivacyLevel(self,zid):
        with sqlite3.connect(self.DBname) as conn:
            c = conn.cursor()
            c.execute(f"select PRIVACY_LEVEL from account_setting where ZID = (?)",[zid])
            result = c.fetchone()
            if result:
                return result[0]
            else:
                return '0'

    def SetPrivacyLevel(self,zid,level):
        with sqlite3.connect(self.DBname) as conn:
            c = conn.cursor()
            c.execute("update account_setting set PRIVACY_LEVEL = (?) where ZID = (?)",[level,zid])
            conn.commit()



    def UpdateUserInfo(self,zid,Info_dict):
        """
        part of indor dict
        Info_dict = {'home_suburb': None,
                    'courses': [], 'full_name': None, 'birthday': None,
                    'email': None, 'program': None,
                    'home_longitude': None,'home_latitude': None}
        """
        settings = []
        values = []
        for key,value in Info_dict.items():
            if key in ['courses']:
                value = ','.join(value)
            settings.append(f"{key.upper()} = (?)")
            values.append(value)
        setting_str = ",".join(settings)
        values.append(zid)
        with sqlite3.connect(self.DBname) as conn:
            c = conn.cursor()
            c.execute(f"update user_info set {setting_str} where ZID = (?)",values)
            conn.commit()
