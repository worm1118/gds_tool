from support.expand.rclone import SupportRclone

from .setup import *


class ModuleRequest(PluginModuleBase):

    def __init__(self, P):
        super(ModuleRequest, self).__init__(P, name='request', first_menu='setting')
        self.db_default = {
            f'{self.name}_db_version' : '1',
            f'{self.name}_remote_path' : '',
            'request_item_last_list_option': '',
            f'request_sourceid': '',
            f'request_target_folderid': '',
            f'{self.name}_db_delete_day' : '30',
            f'{self.name}_db_auto_delete' : 'False',
        }
        self.web_list_model = ModelRequestItem
        

    def process_command(self, command, arg1, arg2, arg3, req):
        ret = {'ret':'success'}
        if command == 'add_copy_force':
            count = 0
            fail = 0
            for db_id in arg1.split(','):
                db_id = db_id.strip()
                if db_id == '':
                    continue
                result = self.add_copy_force(db_id)
                #logger.debug(d(result))
                if result['ret'] == 'success':
                    count += 1
                else:
                    fail += 1
            ret['msg'] = f"{count}개 요청" + (f"<br>{fail}개 실패" if fail>0 else "")
        elif command == 'db_delete':
            if self.web_list_model.delete_by_id(arg1):
                ret['msg'] = '삭제하였습니다.'
            else:
                ret['ret'] = 'warning'
                ret['msg'] = '삭제 실패'
        elif command == 'lsjson1':
            remote = "worker" + ":{{{id}}}".format(id=arg1)
            ret['json'] = P.SupportRcloneWorker.lsjson(remote)
            P.ModelSetting.set('request_sourceid', arg1)
        elif command == 'size':
            remote = "worker" + ":{{{id}}}".format(id=arg1)
            ret['json'] = P.SupportRcloneWorker.size(remote)
            P.ModelSetting.set('request_sourceid', arg1)
        elif command == 'lsjson2':
            ret['json'] = SupportRclone.lsjson(arg1)
            P.ModelSetting.set('request_target_folderid', arg1)
        elif command == 'copy':
            self.direct_request(arg1, arg2)
            ret['msg'] = '복사 요청하였습니다.'
        return jsonify(ret)


    def process_normal(self, sub, req):
        try:
            if sub == 'copy_completed':
                clone_folder_id = req.form['clone_folder_id']
                client_db_id = req.form['client_db_id']
                logger.debug(f'copy_complted: {client_db_id}, {clone_folder_id}')
                self.do_download(client_db_id, clone_folder_id)
                ret = {'ret':'success'}
                return jsonify(ret)
            elif sub == 'callback':
                about = req.form['about']
                client_db_id = req.form['client_db_id']
                ret = req.form['ret']
                logger.debug('about : %s, client_db_id : %s, ret : %s', about, client_db_id, ret)
                if about == 'request':
                    item = ModelRequestItem.get_by_id(client_db_id)
                    item.status = req.form['ret']
                    item.save()
                ret = {'ret':'success'}
                return jsonify(ret)
        except Exception as e: 
            logger.error(f"Exception:{str(e)}")
            logger.error(traceback.format_exc())


    def process_api(self, sub, req):
        try:
            if sub == 'add_copy_2024':
                folder_id = req.form['folder_id']
                folder_name = req.form['folder_name']
                board_type = req.form['board_type']
                category_type = req.form['category_type']
                size = int(req.form['size'])
                count = int(req.form['count'])
                ddns = req.form['ddns']
                copy_type = req.form['copy_type']
                #if ddns != F.SystemModelSetting.get('ddns'):
                #    return {'ret':'wrong_ddns'}
                ret = self.add_copy(folder_id, folder_name, board_type, category_type, size, count, copy_type=copy_type)
                return jsonify(ret)
        except Exception as e: 
            logger.error(f"Exception:{str(e)}")
            logger.error(traceback.format_exc())


    def get_setting_remote_path(self, board_type, category_type):
        try:
            tmp = P.ModelSetting.get_list(f'{self.name}_remote_path')
            remote_list = {}
            for t in tmp:
                t2 = t.split('=')
                if len(t2) == 2 and t2[1].strip() != '':
                    remote_list[t2[0].strip()] = t2[1].strip()
            keys = [f"{board_type},{category_type}", board_type, 'default']

            for key in keys:
                if key in remote_list:
                    return remote_list[key]
        except Exception as e: 
            logger.error(f"Exception:{str(e)}")
            logger.error(traceback.format_exc())

    
    def can_use_request(self, remote_path):
        try:
            size_data = SupportRclone.size('%s:{1PwFA8w365qiPHtVQpqy_qmkQmRtklT5x}' % remote_path.split(':')[0])
            if size_data['count'] == 1 and size_data['bytes'] == 7:
                return True
        except Exception as e: 
            logger.error(f"Exception:{str(e)}")
            logger.error(traceback.format_exc())
        return False


    def add_copy(self, source_id, folder_name, board_type, category_type, size, count, copy_type='folder', remote_path=None):
        try:
            ret = {'ret':'fail', 'remote_path':remote_path, 'server_response':None}

            if ret['remote_path'] is None:
                ret['remote_path'] = self.get_setting_remote_path(board_type, category_type)
            if ret['remote_path'] is None:
                ret['ret'] = 'remote_path_is_none'
                return ret

            already_item = ModelRequestItem.get_by_source_id(source_id)
            if already_item is not None:
                ret['ret'] = 'already'
                ret['status'] = already_item.status
                ret['request_db_id'] = already_item.id
                return ret
            
            can_use_share_flag = self.can_use_request(ret['remote_path'])
            if not can_use_share_flag:
                ret['ret'] = 'cannot_access'
                return ret
            
            item = ModelRequestItem()
            item.copy_type = copy_type
            item.source_id = source_id
            item.target_name = folder_name
            item.board_type = board_type
            item.category_type = category_type
            item.size = size
            item.count = count
            item.remote_path = ret['remote_path']
            item.save()

            lsf_data = SupportRclone.lsf(ret['remote_path'])
            if lsf_data != None and len(lsf_data) == 1 and 'Failed' in lsf_data[0]:
                item.status = "fail_remote_path_is_wrong"
                item.save()
                return ret

            ret = self.add_copy_thread_start(item, ret)
        except Exception as e: 
            logger.error(f"Exception:{str(e)}")
            logger.error(traceback.format_exc())
            ret['ret'] = 'fail'
            ret['log'] = str(e)
        return ret


    def add_copy_force(self, item_id):
        try:
            item = ModelRequestItem.get_by_id(item_id)
            logger.debug(f'복사 재요청!!!!! {item_id}')
            ret = {'ret':'fail', 'remote_path':item.remote_path, 'server_response':None}
            can_use_share_flag = self.can_use_request(ret['remote_path'])
            if not can_use_share_flag:
                ret['ret'] = 'cannot_access'
                return ret
            ret = self.add_copy_thread_start(item, ret)
        except Exception as e: 
            logger.error(f"Exception:{str(e)}")
            logger.error(traceback.format_exc())
            ret['ret'] = 'fail'
            ret['log'] = str(e)
        return ret


    def add_copy_thread_start(self, db_item, ret):
        try:
            version = SupportRclone.get_version()
            version = version.split('\n')[0]
            mod_version = int(version.split('-')[1])
            P.logger.info(f"Rclone version: {version} mod version: {mod_version}")
            
            thread = threading.Thread(target=self.client_copy, args=(db_item.id,))
            thread.setDaemon(True)
            thread.start()
            ret['ret'] = 'success'
            ret['request_db_id'] = db_item.id
            return ret
        except Exception as e: 
            logger.error(f"Exception:{str(e)}")
            logger.error(traceback.format_exc())
            ret['ret'] = 'fail'
            ret['log'] = str(e)
        return ret


    # thread로 동작
    def client_copy(self, db_id):
        try:
            db_item = ModelRequestItem.get_by_id(int(db_id))
            data = db_item.as_dict()
            PP = F.PluginManager.get_plugin_instance('sjva')
            data['sjva_id'] = PP.ModelSetting.get('sjva_id')
            #P.logger.error(d(data))
            copy_ret = P.SupportRcloneWorker.gds_copy(data)
            P.logger.info(f"결과: {copy_ret['status']}")
            self.do_process_result(db_id, copy_ret)
        except Exception as e: 
            logger.error(f"Exception:{str(e)}")
            logger.error(traceback.format_exc())


    def do_process_result(self, db_id, result):
        def func():
            try:
                item = ModelRequestItem.get_by_id(int(db_id))
                if item is None:
                    logger.error('CRITICAL ERROR:%s', db_id)
                    return
                item.status = result['status']
                item.clone_folderid = result['folder_id']
                item.completed_time = datetime.now()
            except Exception as e: 
                logger.error(f"Exception:{str(e)}")
                logger.error(traceback.format_exc())
                item.status = 'fail_download_exception'
            finally:
                if item is not None:
                    item.save()
        thread = threading.Thread(target=func, args=())
        thread.setDaemon(True)
        thread.start()


    def direct_request(self, source_id, remote_path):
        def func(self, source_id, remote_path):
            remote = "worker" + ":{{{id}}}".format(id=source_id)
            try:
                size_data = P.SupportRcloneWorker.size(remote)
                if size_data['count'] > 1000:
                    data = {'title':'요청 실패', 'data' : f"파일 수 {size_data['count']}"}
                    F.socketio.emit("modal", data, namespace='/framework', to='all')
                    return
            except:
                data = {'title':'요청 실패', 'data' : "접근 불가"}
                F.socketio.emit("modal", data, namespace='/framework', to='all')
                return
            #ret = self.add_copy(source_id, "", "direct", "", size_data['bytes'], size_data['count'], copy_type='folder' if len(lsjson) > 0 else "file", remote_path=remote_path)
            ret = self.add_copy(source_id, "", "direct", "", size_data['bytes'], size_data['count'], copy_type='folder', remote_path=remote_path)
            #logger.error(ret)
            if ret['ret'] == 'already':
                data = {'title':'요청 실패', 'data' : "DB에 있음"}
                F.socketio.emit("modal", data, namespace='/framework', to='all')
                return
 
        thread = threading.Thread(target=func, args=(self, source_id, remote_path))
        thread.setDaemon(True)
        thread.start()





class ModelRequestItem(ModelBase):
    P = P
    __tablename__ = 'request_item'
    __table_args__ = {'mysql_collate': 'utf8_general_ci'}
    __bind_key__ = P.package_name

    id = db.Column(db.Integer, primary_key=True)
    created_time = db.Column(db.DateTime)

    copy_type = db.Column(db.String) # folder, file
    source_id = db.Column(db.String)
    target_name = db.Column(db.String) # 폴더면 폴더명, 파일이면 파일명

    call_from = db.Column(db.String)
    board_type = db.Column(db.String)
    category_type = db.Column(db.String)
    remote_path = db.Column(db.String) 
    size = db.Column(db.Integer)
    count = db.Column(db.Integer)

    status = db.Column(db.String) # 'ready' 'request' 'clone' 'completed'
    clone_completed_time = db.Column(db.DateTime)
    completed_time = db.Column(db.DateTime)
    request_time = db.Column(db.DateTime)

    clone_folderid = db.Column(db.String) 


    def __init__(self):
        self.created_time = datetime.now()
        self.status = 'ready'

    @classmethod
    def get_by_source_id(cls, source_id):
        with F.app.app_context():
            return db.session.query(cls).filter_by(source_id=source_id).first()
    
    
    @classmethod
    def make_query(cls, req, order='desc', search='', option1='all', option2='all'):
        with F.app.app_context():
            query = db.session.query(cls)
            query = cls.make_query_search(F.db.session.query(cls), search, cls.target_name)

            if option1 != 'all':
                query = query.filter(cls.board_type == option1)
            if option2 != 'all':
                query = query.filter(cls.status.like(option2 + '%'))
            query = query.order_by(desc(cls.id)) if order == 'desc' else query.order_by(cls.id)
            return query  

