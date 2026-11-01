<?php
declare(strict_types=1);
if (!defined('ITIF_ENTRY')) { http_response_code(404); exit; }
ini_set('display_errors','0');
const GUARD = "<?php exit; ?>\n";
function headers_itif(string $type='application/json; charset=utf-8'): void {
    header('Content-Type: '.$type);header('Cache-Control: no-store');header('X-Content-Type-Options: nosniff');header('X-Frame-Options: DENY');header('Referrer-Policy: no-referrer');
}
function respond(array $data,int $code=200): never { http_response_code($code);echo json_encode($data,JSON_UNESCAPED_UNICODE|JSON_INVALID_UTF8_SUBSTITUTE);exit; }
function config_itif(): array {
    $c=require __DIR__.'/config.example.php';
    if(is_file(__DIR__.'/config.php')) $c=array_replace($c,require __DIR__.'/config.php');
    foreach(['owner','repo','branch'] as $k) if(!is_string($c[$k]) || !preg_match('/\A[A-Za-z0-9_.-]{1,100}\z/D',$c[$k])) throw new RuntimeException('Invalid repository');
    return $c;
}
function read_guard(string $path): ?array {
    $raw=@file_get_contents($path);if($raw===false || !str_starts_with($raw,GUARD))return null;
    $v=json_decode(substr($raw,strlen(GUARD)),true);return is_array($v)?$v:null;
}
function write_guard(string $path,array $value): void {
    $tmp=$path.'.'.bin2hex(random_bytes(4)).'.tmp.php';
    if(file_put_contents($tmp,GUARD.json_encode($value,JSON_UNESCAPED_UNICODE|JSON_INVALID_UTF8_SUBSTITUTE))===false)throw new RuntimeException('Cache unavailable');
    if(!rename($tmp,$path)){@unlink($tmp);throw new RuntimeException('Cache unavailable');}
}
function runtime_itif(): string {
    $p=__DIR__.'/runtime';if(!is_dir($p)&&!@mkdir($p,0750,true))throw new RuntimeException('Cache unavailable');return $p;
}
function remote_itif(string $url,int $limit=4000000,int $seconds=4): string {
    if(!function_exists('curl_init'))throw new RuntimeException('cURL unavailable');
    $host=parse_url($url,PHP_URL_HOST);
    if(!in_array($host,['raw.githubusercontent.com','api.mymemory.translated.net'],true) || parse_url($url,PHP_URL_SCHEME)!=='https')throw new RuntimeException('Invalid upstream');
    $curl=curl_init($url);$body='';
    curl_setopt_array($curl,[CURLOPT_FOLLOWLOCATION=>false,CURLOPT_PROTOCOLS=>CURLPROTO_HTTPS,CURLOPT_CONNECTTIMEOUT=>2,CURLOPT_TIMEOUT=>$seconds,CURLOPT_SSL_VERIFYPEER=>true,CURLOPT_SSL_VERIFYHOST=>2,CURLOPT_USERAGENT=>'ITIF/0.2 public-reader',CURLOPT_WRITEFUNCTION=>static function($ch,$chunk)use(&$body,$limit){if(strlen($body)+strlen($chunk)>$limit)return 0;$body.=$chunk;return strlen($chunk);}]);
    if(curl_exec($curl)===false || curl_getinfo($curl,CURLINFO_RESPONSE_CODE)!==200)throw new RuntimeException('Upstream unavailable');
    return $body;
}
function valid_snapshot(?array $v): bool {
    if(!$v || ($v['schema']??0)!==1 || !is_string($v['generated_at']??null) || !isset($v['status']['feeds'],$v['status']['markets'],$v['editorial'],$v['editions']))return false;
    if(!is_array($v['status']['feeds'])||count($v['status']['feeds'])>200)return false;
    foreach($v['status']['feeds'] as $f)if(!is_array($f)||($f['private']??false)||!is_array($f['items']??null)||!is_string($f['name']??null))return false;
    return true;
}
function snapshot_itif(): array {
    $dir=runtime_itif();$path=$dir.'/snapshot.php';$c=config_itif();$cache=read_guard($path);$ttl=max(60,min(3600,(int)$c['ttl']));
    if(!$cache || time()-($cache['checked']??0)>$ttl){
        $lock=fopen($dir.'/snapshot-lock.php','c+');
        if($lock && flock($lock,LOCK_EX|LOCK_NB)){
            try{
                $again=read_guard($path);
                if($again && time()-($again['checked']??0)<$ttl)$cache=$again;
                else {
                    $url='https://raw.githubusercontent.com/'.$c['owner'].'/'.$c['repo'].'/'.$c['branch'].'/public-data/snapshot.json';
                    $value=json_decode(remote_itif($url),true);
                    if(!valid_snapshot($value))throw new RuntimeException('Invalid public snapshot');
                    $cache=['checked'=>time(),'value'=>$value,'error'=>''];write_guard($path,$cache);
                }
            }catch(Throwable $e){$cache=['checked'=>time(),'value'=>$cache['value']??null,'error'=>'远程数据暂不可用，正在展示上次公开快照'];write_guard($path,$cache);}
            finally{flock($lock,LOCK_UN);fclose($lock);}
        }elseif($lock)fclose($lock);
    }
    $value=$cache['value']??read_guard(__DIR__.'/seed.php');
    if(!valid_snapshot($value))throw new RuntimeException('No public snapshot');
    $stamp=strtotime($value['generated_at']);$age=$stamp===false?PHP_INT_MAX:time()-$stamp;
    $value['status']['delivery']=['generated_at'=>$value['generated_at'],'stale'=>$age>7200,'error'=>$cache['error']??'','mode'=>'公开浏览版'];
    return $value;
}
function xml_itif(string $s): string {return htmlspecialchars($s,ENT_XML1|ENT_QUOTES|ENT_SUBSTITUTE,'UTF-8');}
function rss_itif(array $feeds): string {
    $out='<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>ITIF 信息台</title><link>https://itif.cn/</link><description>公开来源聚合 · 点击标题阅读原文</description>';$seen=[];
    foreach($feeds as $f)foreach($f['items'] as $a){$url=$a['url']??'';if(!preg_match('~\Ahttps?://~i',$url)||isset($seen[$url]))continue;$seen[$url]=true;$out.='<item><title>'.xml_itif($a['title']).'</title><link>'.xml_itif($url).'</link><guid>'.xml_itif($url).'</guid><description>'.xml_itif($f['name']).'</description></item>';}
    return $out.'</channel></rss>';
}
function translate_itif(): never {
    $origin=$_SERVER['HTTP_ORIGIN']??'';$p=parse_url($origin);
    $https=($_SERVER['HTTPS']??'')!=='' && ($_SERVER['HTTPS']??'')!=='off';
    $expected=($https?'https':'http').'://'.($_SERVER['HTTP_HOST']??'');
    if($origin!==$expected)respond(['error'=>'Invalid Origin'],403);
    if((int)($_SERVER['CONTENT_LENGTH']??0)>20000)respond(['error'=>'Too large'],413);
    $raw=file_get_contents('php://input',false,null,0,20001);if(strlen($raw)>20000)respond(['error'=>'Too large'],413);
    $a=json_decode($raw,true);$target=$a['target']??'';$texts=$a['texts']??null;
    if(!in_array($target,['zh-CN','en'],true)||!is_array($texts)||!array_is_list($texts)||count($texts)>4)respond(['error'=>'Invalid translation request'],400);
    foreach($texts as $t)if(!is_string($t)||strlen($t)>6400||!preg_match('//u',$t))respond(['error'=>'Invalid text'],400);
    $dir=runtime_itif();$lock=fopen($dir.'/translate-lock.php','c+');
    if(!$lock || !flock($lock,LOCK_EX|LOCK_NB))respond(['error'=>'Translation busy'],429);
    try{
        $store=read_guard($dir.'/translations.php')??[];$day=gmdate('Y-m-d');if(($store['day']??'')!==$day)$store=['day'=>$day,'used'=>0,'cache'=>[]];
        $results=[];$c=config_itif();
        foreach($texts as $text){
            $key=hash('sha256',$target."\0".$text);
            if(isset($store['cache'][$key])){$results[]=['text'=>$store['cache'][$key],'error'=>''];continue;}
            preg_match_all('/./us',$text,$chars);$count=count($chars[0]);
            if($store['used']+$count>min(4500,max(0,(int)$c['translation_daily_chars']))){$results[]=['text'=>$text,'error'=>'本站免费翻译额度已用完，请稍后重试'];continue;}
            $store['used']+=$count;write_guard($dir.'/translations.php',$store);$chunks=[];$chunk='';
            foreach($chars[0] as $char){if(strlen($chunk.$char)>450){$chunks[]=$chunk;$chunk='';}$chunk.=$char;}if($chunk!=='')$chunks[]=$chunk;
            try{
                $translated='';$deadline=microtime(true)+8;
                foreach($chunks as $part){if(microtime(true)>$deadline)throw new RuntimeException('Timeout');$lang=$target==='en'?'zh-CN|en':'en|zh-CN';$data=json_decode(remote_itif('https://api.mymemory.translated.net/get?'.http_build_query(['q'=>$part,'langpair'=>$lang]),100000,3),true);if(($data['responseStatus']??0)!==200||!is_string($data['responseData']['translatedText']??null))throw new RuntimeException('Translation unavailable');$translated.=html_entity_decode($data['responseData']['translatedText'],ENT_QUOTES|ENT_HTML5,'UTF-8');}
                $store['cache'][$key]=$translated;$results[]=['text'=>$translated,'error'=>''];
            }catch(Throwable $e){$results[]=['text'=>$text,'error'=>'免费翻译暂不可用，保留原文'];}
        }
        $store['cache']=array_slice($store['cache'],-1500,null,true);write_guard($dir.'/translations.php',$store);
    }finally{flock($lock,LOCK_UN);fclose($lock);}
    respond(['results'=>$results]);
}
