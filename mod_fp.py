from support import SupportDiscord

from .setup import *


class ModuleFP(PluginModuleBase):

    def __init__(self, P):
        super(ModuleFP, self).__init__(P, name='fp', first_menu='setting')
        self.db_default = {
            f'{self.name}_db_version' : '4',
            f'{self.name}_use_plexscan' : 'False',
            f'{self.name}_ignore_rule' : '',
            f'{self.name}_change_rule' : '',
            f'fp_item_last_list_option' : '',
            f'{self.name}_db_delete_day' : '30',
            f'{self.name}_db_auto_delete' : 'False',
            f'{self.name}_broadcast_path' : '/ROOT/GDRIVE/VIDEO',
        }
        self.web_list_model = ModelFPItem

    def process_discord_data(self, data):
        #P.logger.warning(d(data))
        try:
            db_item = ModelFPItem.process_discord_data(data)

            if P.ModelSetting.get_bool(f'{self.name}_use_plexscan') == False:
                return
            ignore_list = P.ModelSetting.get_list(f'{self.name}_ignore_rule')
            for ignore in ignore_list:
                if ignore in db_item.gds_path:
                    db_item.status = 'IGNORE'
                    db_item.save()
                    return
            change_list = P.ModelSetting.get_list(f'{self.name}_change_rule')
            ret = db_item.gds_path
            if ret == None: return
            for rule in change_list:
                tmp = rule.split('|')
                ret = ret.replace(tmp[0].strip(), tmp[1].strip())
            if ret[0] != '/':
                ret = ret.replace('/', '\\')

            db_item.local_path = ret

            PP = F.PluginManager.get_plugin_instance('plex_mate')
            #PP.ModelScanItem(ret, mode="ADD", callback_id=f"gds_tool_{db_item.id}", callback_url=ToolUtil.make_apikey_url("/gds_tool/normal/fp/scan_completed")).save()
            PP.ModelScanItem(ret, mode=db_item.scan_mode, callback_id=f"gds_tool_{db_item.id}", callback_url=ToolUtil.make_apikey_url("/gds_tool/normal/fp/scan_completed")).save()

            db_item.status = "SCAN_REQUEST"
            db_item.save()
        except Exception as e: 
            P.logger.error(f"Exception:{str(e)}")
            P.logger.error(traceback.format_exc())

    
    def process_normal(self, sub, req):
        #P.logger.error(sub)
        #P.logger.error(d(req.form))
        try:
            if sub == 'scan_completed':
                callback_id = req.form['callback_id']
                db_item = ModelFPItem.get_by_id(callback_id.split('_')[-1])
                db_item.status = req.form['status']
                db_item.save()
                return jsonify({'ret':'success'})
        except Exception as e: 
            P.logger.error(f"Exception:{str(e)}")
            P.logger.error(traceback.format_exc())

    def process_command(self, command, arg1, arg2, arg3, req):
        if command == 'broadcast':
            arg2 = arg2.rstrip('/')
            P.ModelSetting.set(f'{self.name}_broadcast_path', arg2)
            return self.do_broadcast(arg2, arg1)

    def process_api(self, sub, req):
        if sub == 'broadcast':
            return self.do_broadcast(req.args.get('gds_path'), req.args.get('scan_mode', 'ADD'))
    
    def do_broadcast(self, gds_path, scan_mode):
        try:
            ret = {'ret':'success'}
            gds_path = gds_path.rstrip('/')
            tmps = gds_path.split('/')
            if len(tmps) < 7:
                ret['ret'] = 'error'
                ret['msg'] = '범위가 너무 큽니다.'
            elif tmps[-1] in ['0Z', '가', '나', '다', '라', '마', '바', '사', '아', '자', '차', '카', '타', '파', '하']:
                    ret['ret'] = 'warning'
                    ret['msg'] = '컨텐츠 폴더 혹은 파일을 지정하세요.'
            elif gds_path.startswith('/ROOT/GDRIVE') == False:
                ret['ret'] = 'error'
                ret['msg'] = '/ROOT/GDRIVE 로 시작해야 합니다.'
            else:
                bot = {
                    't1': 'gds_tool',
                    't2': 'fp',
                    't3': 'user',
                    'data': {
                        'gds_path': gds_path,
                        'scan_mode': scan_mode,
                    }
                }
                SupportDiscord.send_discord_bot_message(json.dumps(bot), "https://discord.com/api/webhooks/1250002567623344171/oeDaF6COyoVzqdw0BZk3qgT4hsKtmpqjdQJTTVRS-fCq0gBM7-J7rr52fXnziiAhkWT1")
                ret['msg'] = '전송하였습니다.'
            return jsonify(ret)
        except Exception as e: 
            P.logger.error(f"Exception:{str(e)}")
            P.logger.error(traceback.format_exc())
            ret['ret'] = 'error'
            ret['msg'] = str(e)
        return jsonify(ret)


    def migration(self):
        try:
            import sqlite3
            db_file = F.app.config['SQLALCHEMY_BINDS'][P.package_name].replace('sqlite:///', '').split('?')[0]
            #logger.error(db_file)
            #if P.ModelSetting.get(f'{self.name}_db_version') == '3':
            if P.ModelSetting.get(f'{self.name}_db_version') in ['1', '2', '3']:
                with F.app.app_context():
                    connection = sqlite3.connect(db_file)
                    cursor = connection.cursor()
                    query = f'ALTER TABLE "{self.name}_item" ADD scan_mode VARCHAR'
                    cursor.execute(query)
                    connection.close()
                    P.ModelSetting.set(f'{self.name}_db_version', '4')
                    db.session.flush()
        except Exception as e:
            logger.error(f"Exception:{str(e)}")
            logger.error(traceback.format_exc())




class ModelFPItem(ModelBase):
    P = P
    __tablename__ = 'fp_item'
    __table_args__ = {'mysql_collate': 'utf8_general_ci'}
    __bind_key__ = P.package_name

    id = db.Column(db.Integer, primary_key=True)
    created_time = db.Column(db.DateTime)

    mode = db.Column(db.String)
    data = db.Column(db.JSON)
    status = db.Column(db.String)
    gds_path = db.Column(db.String)
    local_path = db.Column(db.String)
    scan_mode = db.Column(db.String)

    def __init__(self):
        self.created_time = datetime.now()
        self.status = 'READY'

    
    @classmethod
    def make_query(cls, req, order='desc', search='', option1='all', option2='all'):
        with F.app.app_context():
            query = db.session.query(cls)
            query = cls.make_query_search(F.db.session.query(cls), search, cls.gds_path)

            if option1 != 'all':
                query = query.filter(cls.mode == option1)
            if option2 != 'all':
                query = query.filter(cls.status.like(option2 + '%'))
            query = query.order_by(desc(cls.id)) if order == 'desc' else query.order_by(cls.id)
            return query  

    @classmethod
    def process_discord_data(cls, data):
        try:
            P.logger.debug(data)
            db_item = ModelFPItem()
            if data['ch'] == 'bot_gds_vod':
                db_item.mode = 'VOD'
                db_item.scan_mode = 'ADD'
                db_item.data = data
                db_item.gds_path = data['msg']['data']['r_fold'] + '/' + data['msg']['data']['r_file']
            elif data['ch'] == 'bot_gds_movie':
                db_item.mode = 'MOVIE'
                db_item.scan_mode = 'ADD'
                db_item.data = data
                db_item.gds_path = data['msg']['data']['gds_path']
            elif data['ch'] == 'bot_gds_av':
                db_item.mode = 'AV'
                db_item.scan_mode = 'ADD'
                db_item.data = data
                db_item.gds_path = data['msg']['data']['gds_path']
            elif data['ch'] == 'bot_gds_user':
                db_item.mode = 'USER'
                db_item.scan_mode = data['msg']['data']['scan_mode']
                db_item.data = data
                db_item.gds_path = data['msg']['data']['gds_path']
            db_item.save()
            return db_item
        except Exception as e:
            P.logger.error(f"Exception:{str(e)}")
            P.logger.error(traceback.format_exc())   