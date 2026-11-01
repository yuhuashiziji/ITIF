<?php
declare(strict_types=1);
define('ITIF_ENTRY',true);require __DIR__.'/lib.php';headers_itif();
try {
    $action=$_GET['action']??'';$method=$_SERVER['REQUEST_METHOD']??'GET';
    if($action==='translate'){if($method!=='POST')respond(['error'=>'Method not allowed'],405);translate_itif();}
    if(!in_array($action,['status','editorial','edition','rss','health'],true))respond(['error'=>'Not found'],404);
    if($method!=='GET')respond(['error'=>'公开站点不允许修改来源或配置'],405);
    $v=snapshot_itif();
    if($action==='status')respond($v['status']);
    if($action==='editorial')respond($v['editorial']);
    if($action==='health')respond(['ok'=>true,'php'=>PHP_MAJOR_VERSION.'.'.PHP_MINOR_VERSION,'delivery'=>$v['status']['delivery']]);
    if($action==='edition'){$date=$_GET['date']??'';if(!is_string($date)||!preg_match('/\A\d{4}-\d{2}-\d{2}\z/',$date))respond(['error'=>'Invalid date'],400);respond($v['editions'][$date]??['error'=>'Not found'],isset($v['editions'][$date])?200:404);}
    headers_itif('application/rss+xml; charset=utf-8');echo rss_itif($v['status']['feeds']);
}catch(Throwable $e){respond(['error'=>'公开数据暂不可用，请稍后重试'],503);}
