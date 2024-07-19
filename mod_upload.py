from support import SupportFile
from support.expand.rclone import SupportRclone
from tool import ToolModalCommand

from .setup import *


class ModuleUpload(PluginModuleBase):

    def __init__(self, P):
        super(ModuleUpload, self).__init__(P, name='upload', first_menu='action')
        self.db_default = {
            f'{self.name}_rule_filesystem' : '',
            f'{self.name}_rule_plex' : '',

            f'{self.name}_remote_path' : '',
        }
    
    def process_command(self, command, arg1, arg2, arg3, req):
        ret = {'ret':'success'}
        if command == 'category_list':
            ret['data'] = category_list
        elif command == 'size':
            P.ModelSetting.set(f'{self.name}_remote_path', arg1)
            ret = SupportRclone.size(arg1)
        elif command == 'meta_info':
            title = re.sub('\[.*?\]', '', arg1)
            match = re.compile(r'\(\d{4}\)').search(title)
            year = None
            if match:
                title = title.replace(match.group(0), '').strip()
                year = match.group(0).replace('(', '').replace(')', '')
            if year != None:
                year = int(year)
            board_type = arg2
            if board_type == 'share_movie':
                mod_movie = F.PluginManager.get_plugin_instance('metadata').logic.get_module('movie')
                data = mod_movie.search(title, year, site_list=['tmdb'], site_all=True)
                for item in data:
                    item['folder_name'] = f"{SupportFile.text_for_filename(item['title'])}"
                    if item['title_en'] != '':
                        item['folder_name'] += f" [{SupportFile.text_for_filename(item['title_en'])}]"
                    item['folder_name'] += f" ({item['year']})"
                ret['data'] = data
            elif board_type == 'share_ktv':
                mod_ktv = F.PluginManager.get_plugin_instance('metadata').logic.get_module('ktv')
                data = mod_ktv.search(title)
                ret['data'] = data
            else:
                mod_ftv = F.PluginManager.get_plugin_instance('metadata').logic.get_module('ftv')
                data = mod_ftv.search(title, year=year)
                ret['data'] = data
            return jsonify(ret)
        elif command == 'upload':
            self.upload(arg1)
        elif command == 'search_plex':
            PP = F.PluginManager.get_plugin_instance('plex_mate')
            if PP == None:
                ret['msg'] = 'PLEX MATE 플러그인이 없습니다.'
                return jsonify(ret)
            data = PP.PlexDBHandle.get_media_parts_file_like(arg1)
            folder_list = []
            for item in data:
                tmp = os.path.dirname(item['file'])
                for _ in folder_list:
                    if _['folder'] == tmp:
                        _['files'].append(os.path.basename(item['file']))
                        break
                else:
                    folder_list.append({
                        'folder': tmp,
                        'files': [os.path.basename(item['file'])]
                    })
            rules = P.ModelSetting.get_list(f'{self.name}_rule_plex', '\n')
            for folder in folder_list:
                remote = folder['folder']
                for rule_item in rules:
                    tmp = rule_item.split('|')
                    remote = remote.replace(tmp[0], tmp[1])
                remote = remote.replace('\\', '/')
                folder['remote'] = remote
            ret['data'] = folder_list
            return ret
        elif command == 'search_local':
            rules = P.ModelSetting.get_list(f'{self.name}_rule_filesystem', '\n')
            remote = arg1
            for rule_item in rules:
                tmp = rule_item.split('|')
                remote = remote.replace(tmp[0], tmp[1])
            if ':' not in remote:
                ret['ret'] = 'warning'
                ret['msg'] = "매칭 규칙이 없습니다."
            else:
                remote = remote.replace('\\', '/')
                ret['data'] = remote
                return ret
        return jsonify(ret)


    def upload(self, arg1):
        try:
            def add_text(msg):
                F.socketio.emit("command_modal_add_text", msg, namespace='/framework', broadcast=True)
            
            data = self.arg_to_dict(arg1)
            try:
                #P.logger.error('{' + data['meta_info'].split('{',1)[1].rsplit('}',1)[0] + '}')
                data['meta_info'] = json.loads('{' + data['meta_info'].split('{',1)[1].rsplit('}',1)[0] + '}')
            except:
                if data['board_type'] in ['share_movie', 'share_ftv', 'share_ktv']:
                    if data['category_type'] != 'etc':
                        add_text("MOVIE, KTV, FTV는 메타 선택 필수.\n")
                        add_text("메타가 없는 경우 기타 카테고리만 가능.\n")
                        add_text('\n모두 완료되었습니다.\n')
                        return
            upload_folderid = '16Wcqs0W60m0OaX9WU2ePPEy__O35wuYR'
            remote_path = data['upload_remote_path']
            
            # 게시판
            board_type = data['board_type']
            category_type = data['category_type']
            board_title = data['board_title']
            board_content = data['board_content']
            board_meta_url = data['board_meta_url']
            folder_name = data['folder_name']

            size = int(data['size'])
            meta_info = data['meta_info']
            action = data['action']
            PP = F.PluginManager.get_plugin_instance('sjva')
            user_id = PP.get_auth_status().get('sjva_id')
            if board_content.startswith('ID:'):
                user_id = board_content.split('\n')[0].split(':')[1].strip()
                board_content = board_content[board_content.find('\n'):]

            

            def func():
              try:
                #ret = RcloneTool2.do_user_upload(ModelSetting.get('rclone_path'), ModelSetting.get('rclone_config_path'), my_remote_path, folder_name, upload_folderid, board_type, category_type, is_move=(action=='move'))

                ret = {'completed':False, 'folderid':'', 'lsjson':None}
                gdrive_remote = remote_path.split(':')[0]
                server_remote = '{gdrive_remote}:{{{upload_folderid}}}'.format(gdrive_remote=gdrive_remote, upload_folderid=upload_folderid)

                F.socketio.emit("command_modal_clear", None, namespace='/framework', broadcast=True)
                F.socketio.emit("command_modal_show", '업로드', namespace='/framework', broadcast=True)
                add_text('업로드를 시작합니다.\n\n')
                add_text('1. 업로드 가능 테스트.\n')
                
                can_use_share_flag = self.get_module('request').can_use_request(remote_path)
                if can_use_share_flag:
                    add_text('업로드 가능합니다.\n\n')
                else:
                    add_text('업로드 불가능합니다. 구글 그룹스에 가입하세요.\n\n')
                    return ret
                    
                add_text('2. 컨텐츠 크기 및 파일목록.\n')
                ret['lsjson'] = SupportRclone.lsjson(remote_path,  option=['-R', '--files-only'])
                ret['size'] = SupportRclone.size(remote_path)
                add_text(f"파일수 : {ret['size']['count']}\n파일크기 : {ret['size']['bytes']}\n\n")

                add_text('3. 공유드라이브 폴더 생성\n')
                tmp_foldername = "{board_type}^{category_type}^{count}^{bytes}^{folder_name}^{user_id}".format(
                    board_type=board_type,
                    category_type=category_type,
                    count=ret['size']['count'],
                    bytes=ret['size']['bytes'],
                    folder_name=folder_name,
                    user_id=user_id
                )
                upload_remote = '{server_remote}/{tmp_foldername}/{folder_name}'.format(server_remote=server_remote, tmp_foldername=tmp_foldername, folder_name=folder_name)
                SupportRclone.mkdir(upload_remote)
                add_text(f'remote path : {upload_remote}\n\n')

                add_text('4. 생성된 폴더의 ID 정보\n')
                
                for i in range(1, 11):
                    add_text(f'{i}/10. GETID 시도\n')
                    tmp = SupportRclone.getid(upload_remote)
                    if tmp is not None:
                        ret['folder_id'] = tmp
                        break
                    add_text('실패. 10초 후 다시 시도합니다.\n')
                    time.sleep(10)
                add_text('\n')

                if ret['folder_id'] is None:
                    add_text('폴더ID를 얻을 수 없어 중단합니다.\n\n')
                    add_text('이미 폴더는 만들어졌으니, 잠시 후 다시 시도하면 정보를 가져올 수 있습니다.\n\n')
                    return ret
                else:
                    add_text(f"폴더 ID : {ret['folder_id']}\n\n")
                cmd = SupportRclone.rclone_cmd()
                cmd += [action, remote_path, upload_remote, '--drive-server-side-across-configs=true', '-v']

                return_log = ToolModalCommand.start('업로드',
                    [
                        ['msg', '5. Rclone 명령'],
                        cmd,
                        ['msg', 'Rclone 명령을 완료하였습니다.']
                    ], 
                    clear=False, wait=True, show_modal=True
                )
                if (return_log.find('Transferred') != -1 and return_log.find('100%') != -1) or (return_log.find('Checks:') != -1 and return_log.find('100%') != -1):
                    ret['completed'] = True
                    if action == 'move':
                        add_text('purge 명령으로 move 루트 삭제\n')
                        SupportRclone.purge(remote_path)

                add_text(f"업로드 결과 : {'성공' if ret['completed'] else '실패'}\n\n")

                if ret['completed']:
                    if ret['folder_id'] != '':
                        add_text('6. 게시물 등록중...\n')
                        data = {'board_type' : board_type, 'category_type':category_type, 'board_title':board_title, 'board_content':board_content, 'board_meta_url' : board_meta_url, 'folder_name':folder_name, 'size':ret['size'], 'meta_info':meta_info, 'folder_id':ret['folder_id'], 'user_id':user_id, 'lsjson' : ret['lsjson']}
                        if len(data['lsjson']) > 100:
                            data['lsjson'] = data['lsjson'][:100]
                            
                        site_ret = self.site_append(data)
                        add_text(json.dumps(site_ret) + '\n\n')
                    else:
                        add_text('업로드한 폴더ID값을 가져올 수 없어서 사이트 등록에 실패하였습니다.\n관리자에게 등록 요청하세요.\n')
                else:
                    add_text('업로드가 완료되지 않아 게시글이 등록되지 않습니다.\n')
                    add_text('확인 후 다시 시도하세요.\n')
              except Exception as e: 
                add_text(f"에러발생\n")
                add_text(f"Exception:{str(e)}\n")
                add_text(str(traceback.format_exc()))
              finally:
                add_text('\n모두 완료되었습니다.\n')
            thread = threading.Thread(target=func, args=())
            thread.setDaemon(True)
            thread.start()
            return ''
        except Exception as e: 
            add_text(f"에러발생\n")
            add_text(f"Exception:{str(e)}\n")
            add_text(str(traceback.format_exc()))


    def site_append(self, data):
        try:
            import json

            import requests
            res = requests.post(f"{F.config['DEFINE']['WEB_DIRECT_URL']}/ff/ff_share_upload.php", data={'data':json.dumps(data)})
            return res.json()
        except Exception as e: 
            P.logger.error('Exception:%s', e)
            P.logger.error(traceback.format_exc())


category_list = [
    { 
        'type' : 'share_movie', 
        'name' : '영화', 
        'category_list' : ['국내', '외국', '최신', '더빙', '최고품질', '3D', '기타']
    },
    { 
        'type' : 'share_ktv', 
        'name' : '국내TV', 
        'category_list' : ['드라마', '예능', '교양', '어린이', '기타']
    },
    { 
        'type' : 'share_ftv', 
        'name' : '외국TV', 
        'category_list' : ['미드', '일드', '중드', '영드', '다큐', '애니', '더빙', '기타', '방영중']
    },
    { 
        'type' : 'share_music', 
        'name' : '음악', 
        'category_list' : ['국내', '외국', '차트', '클래식', '오디오북', '기타']
    },
    { 
        'type' : 'share_reading', 
        'name' : '리딩', 
        'category_list' : ['일반', '웹툰', '만화고화질', '만화', '웹소설', '라노벨', '화보', '잡지', '기타']
    },
    { 
        'type' : 'share_etc', 
        'name' : '기타', 
        'category_list' : [u'영상', u'SW', '게임', '기타']
    },
]
