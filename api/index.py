import flask
import json
from flask_cors import CORS, cross_origin
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import time

import hashlib
import base64
uri = "mongodb+srv://deffield62:sRT4OhH383U487dA@cluster0.aueykiq.mongodb.net/?retryWrites=true&w=majority"

client = MongoClient(uri, server_api=ServerApi('1'))
db = client.AskBox
collection = db.users

server = flask.Flask(__name__)
cors = CORS(server)

ErrorCode = {
    '10000': 'Success',
    '10011': '该账号已被注册',
    '10012': '该账号尚未注册',
    '10013': '密码错误',
    '10021': '身份校验未通过'
}

def getMd5(text):
    md5Obj = hashlib.md5()
    md5Obj.update(text.encode('utf-8'))
    return md5Obj.hexdigest()

def genToken(textA:str,textB:str):
    print(textA,textB)
    md1 = getMd5(textA)
    md2 = getMd5(textB)
    md3 = getMd5(md1 + textA)
    md4 = getMd5(textA + md2)
    return md3 + md4

def decodeB64Text(text):
    return str(base64.b64decode(text),'utf-8')

def checkIfUserNameExist(username):
    print(collection.find_one({"username": username}))
    return bool(collection.find_one({"username": username}))

def getReturnText(Success, errorcode='10000', others=None):
    result = {
        'success': Success,
        'response': ErrorCode[errorcode],
    }
    if (others):
        result['others'] = others
    return json.dumps(result, ensure_ascii=False)

def checkToken(userId,token):
    return bool(collection.find_one({'userId':userId}).get('token') == token)

def getTextFromBdCode(bdCode):
    a = db.texts.find_one({'bdCode':bdCode})
    a.pop('_id')
    a.pop('bdCode')
    return dict(a)

@server.route('/')
def test():
  return "SUCCESS"

@server.route('/vue-project/login', methods=['post'])
def _vueProject_login():
    dt = flask.request.get_json()
    if (checkIfUserNameExist(dt['username']) == False):
        return getReturnText(False, '10012')
    result = collection.find_one(dt)
    if (bool(result)):
        others = {
            'userId': result['userId'],
            'token': genToken(str(result['userId']),genToken(dt['username'],dt['password']))
        }
        return getReturnText(True, others=others)
    return getReturnText(False, '10013')

@server.route('/vue-project/register', methods=['post'])
def _vueProject_register():
    dt = flask.request.get_json()
    if checkIfUserNameExist(dt['username']):
        return getReturnText(False, '10011')
    userId = str(len(list(collection.find())) + 100001)
    dt['userId'] = userId
    dt['token'] = genToken(userId,genToken(dt['username'],dt['password']))
    others = {
        'userId': userId,
        'token': dt['token']
    }
    result = collection.insert_one(dt)
    return getReturnText(True, others=others)

@server.route('/vue-project/submitText', methods=['post'])
def _vueProject_submitText():
    dt = flask.request.get_json()
    if(checkToken(dt['userId'], dt['token']) == False):
        return getReturnText(False, '10021')
    bdCode = genToken(str(time.time() * 1000),getMd5(dt['text']))
    bdCode = getMd5(bdCode)
    data = {
        'bdCode': bdCode,
        'text': dt['text'],
        'toUser': dt['toUser'],
        'answered':False,
        'answer':''
    }
    result = db.texts.insert_one(data)
    print(result)
    return getReturnText(True, others={'bdCode':bdCode})

@server.route('/vue-project/BangDing', methods=['post'])
def _vueProject_BangDing():
    dt = flask.request.get_json()
    if(checkToken(dt['userId'], dt['token']) == False):
        return getReturnText(False, '10021')
    result = collection.update_one({'userId':dt['userId']}, {'$push': {'questionsBdCode': dt['bdCode']}})
    print(result)
    
    return getReturnText(True)
    
@server.route('/vue-project/getAskedQuestions', methods=['post'])
def _vueProject_getAskedQuestions():
    dt = flask.request.get_json()
    if(checkToken(dt['userId'], dt['token']) == False):
        return getReturnText(False, '10021')
    
    print(dt)
    result = collection.find_one({'userId':dt['userId']})
    if(result and result.get('questionsBdCode')):
        print((result['questionsBdCode']))
        texts = [getTextFromBdCode(i) for i in result['questionsBdCode']]
    else:
        texts = []
    return getReturnText(True,others={'texts':texts})

@server.route('/vue-project/getUserNameFromUserId',methods=['GET'])
def _vueProject_getUserNameFromUserId():
    userId = flask.request.args.get('userId')
    return getReturnText(True,others={'username':collection.find_one({'userId':userId})['username']})

@server.route('/vue-project/getMyQuestions',methods=['post'])
def _vueProject_getMyQuestions():
    dt = flask.request.get_json()
    if(checkToken(dt['userId'], dt['token']) == False):
        return getReturnText(False, '10021')
    
    r = db.texts.find({'toUser':dt['userId']})
    result = []
    for i in r:
        i.pop('_id')
        i.pop('toUser')
        result.append(dict(i))
    print(result)
    return getReturnText(True,others={'texts':result})

@server.route('/vue-project/submitAnswer',methods=['post'])
def _vueProject_submitAnswer():
    dt = flask.request.get_json()
    if(checkToken(dt['userId'], dt['token']) == False):
        return getReturnText(False, '10021')
    
    upd = {
        '$set': {
            'answered': True,
            'answer': dt['answer']
        }
    }
    db.texts.update_one({'bdCode':dt['bdCode']}, upd)
    return getReturnText(True)

    