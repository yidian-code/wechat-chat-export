"""Bounded parsing of embedded WeChat recordinfo/dataitem conversations."""
import hashlib
import xml.etree.ElementTree as ET
from datetime import datetime


def build_forward(data,parent,limit=5000,depth=0,budget=None):
    # Delayed import: reader describes a forward without recursively parsing it.
    from .reader import _xml,_find,_txt,location_details
    budget=budget if budget is not None else [limit]
    title=parent.get('extra',{}).get('title') or '转发的聊天记录'
    result={'title':title,'messages':[],'count':0,'truncated':False}
    payload=parent.get('_forward_xml') or ''
    if depth>=6 or budget[0]<=0:
        result.update(truncated=True,notice='嵌套层数或消息数超过本次处理上限，已保留可读取内容。')
        return result
    if not payload or len(payload)>16*1024*1024:
        result['notice']='这条转发没有附带可读取的逐条明细；仅能保留标题和摘要。'
        return result
    root=_xml(payload)
    if root is None:
        result['notice']='转发明细的格式尚不能解析，已保留标题和摘要。'
        return result
    container=_find(root,'datalist')
    items=container.findall('dataitem') if container is not None else root.findall('dataitem')
    result['title']=root.findtext('title') or title
    result['total']=len(items)
    types={1:(1,'text'),2:(3,'image'),3:(34,'voice'),4:(43,'video'),
           5:(49,'link'),6:(48,'location'),7:(49,'link'),8:(49,'file'),
           17:(49,'chatrecord'),19:(49,'miniprogram'),22:(49,'miniprogram')}
    for index,item in enumerate(items):
        if budget[0]<=0:
            result['truncated']=True;break
        budget[0]-=1
        try:kind_number=int(item.attrib.get('datatype') or item.findtext('datatype') or 0)
        except ValueError:kind_number=0
        base,kind=types.get(kind_number,(0,'other'))
        content=_txt(item,'datadesc') or ''
        name=_txt(item,'sourcename') or _txt(item,'displayname') or '转发消息'
        user=_txt(item,'fromusr') or _txt(item,'realchatname') or ''
        stamp=_txt(item,'srcMsgCreateTime') or _txt(item,'createtime')
        time_text=_txt(item,'sourcetime')
        try:
            timestamp=int(stamp)
            if timestamp>10**12:timestamp//=1000
            if not 0<timestamp<253402300800:raise ValueError()
        except (ValueError,TypeError):
            try:timestamp=int(datetime.strptime(time_text,'%Y-%m-%d %H:%M:%S').timestamp())
            except (ValueError,OverflowError):timestamp=int(parent.get('create_time') or 0)
        try:display_time=datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S') if timestamp else time_text
        except (ValueError,OSError,OverflowError):timestamp=0;display_time=time_text
        source=ET.tostring(item,encoding='unicode')
        identifier=_txt(item,'fromnewmsgid') or item.attrib.get('dataid') or str(index)
        child={'local_id':0,'server_id':identifier,'shard':parent.get('shard',0),
            'type':base,'raw_type':base,'type_name':'转发消息','kind':kind,
            'create_time':timestamp,'time_str':display_time,'sender':name,'sender_wxid':user,
            'avatar_url':_txt(item,'sourceheadurl'),'is_sender':bool(user) and user==data.wxid,
            'session':parent.get('session',''),'text':content,'extra':{},
            '_resource_source':source,'_media':data._media_hints(source,base),
            '_forward_item':True,'_forward_id':hashlib.sha256((str(identifier)+str(index)).encode()).hexdigest()[:20]}
        if item.attrib.get('dataid'):child['_media']['paths'].append(item.attrib['dataid'])
        heading=_txt(item,'datatitle') or _txt(item,'title')
        if kind=='text':child['text']=content or heading
        elif kind in ('image','voice','video'):
            child['text']={'image':'[图片]','voice':'[语音]','video':'[视频]'}[kind]
            if _txt(item,'datafmt').lower() in ('gif','webp') and kind=='image':child['kind']='emoji'
        elif kind=='file':
            child['extra']={'filename':heading or '转发附件','filesize':_txt(item,'datasize')}
            child['text']='[文件] '+child['extra']['filename']
        elif kind=='location':
            child['extra'].update(location_details(item))
            child['text']='[位置] '+(child['extra'].get('title') or content or heading)
        elif kind in ('link','miniprogram'):
            child['extra']={'title':heading or content or '分享卡片','url':_txt(item,'url') or _txt(item,'link'),
                'description':_txt(item,'desc') or content,'source_name':_txt(item,'appname')}
            child['text']=heading or content or '[分享卡片]'
            if kind=='miniprogram':
                child['extra']['miniprogram']={key:_txt(item,tag) for key,tag in
                    (('appid','appid'),('username','username'),('page_path','pagepath'),('icon_url','weappiconurl'))}
        elif kind=='chatrecord':
            nested=_find(item,'recordxml')
            if nested is None:nested=_find(item,'recorditem')
            if nested is not None:
                child['_forward_xml']=nested.text if nested.text and nested.text.strip() else ET.tostring(nested,encoding='unicode')
            child['extra']['title']=heading or content or '转发的聊天记录'
            child['text']='[聊天记录] '+child['extra']['title']
            child['forward']=build_forward(data,child,limit,depth+1,budget)
        elif kind=='other':child['text']=content or heading or '[暂不支持的转发消息类型]'
        # Some record variants embed the original appmsg, including replies.
        if kind!='text' and content.lstrip().startswith(('<msg','<appmsg')) and '<appmsg' in content:
            child['content']=content
            child.update(data._describe_appmsg(child,{'text':content,'extra':{}}))
            embedded=data._media_hints(content,base)
            for key,values in embedded.items():
                child['_media'].setdefault(key,[])
                for value in values:
                    if value not in child['_media'][key]:child['_media'][key].append(value)
            if child.get('_forward_xml') and not child.get('forward'):
                child['forward']=build_forward(data,child,limit,depth+1,budget)
        result['messages'].append(child)
    result['count']=len(result['messages'])
    if result['truncated']:result['notice']='消息数超过本次处理上限，已保留可读取内容。'
    elif not items:result['notice']='这条转发未附带逐条明细；仅能保留标题和摘要。'
    return result
