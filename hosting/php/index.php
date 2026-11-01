<?php
declare(strict_types=1);
define('ITIF_ENTRY',true);require __DIR__.'/lib.php';headers_itif('text/html; charset=utf-8');
try {
    $snapshot=snapshot_itif();$json=json_encode($snapshot['status'],JSON_HEX_TAG|JSON_HEX_AMP|JSON_HEX_APOS|JSON_HEX_QUOT|JSON_INVALID_UTF8_SUBSTITUTE);
    $html=file_get_contents(__DIR__.'/template.php');$html=substr($html,strlen(GUARD));
    echo str_replace('/* ============ 初始渲染 ============ */','window.ITIF_PUBLIC=true;window.__BOOTSTRAP__='.$json.';/* ============ 初始渲染 ============ */',$html);
} catch(Throwable $e){http_response_code(503);echo '<!doctype html><meta charset="utf-8"><h1>ITIF 信息台</h1><p>公开数据尚未就绪。请检查 PHP 缓存目录写入权限和部署文件是否完整。</p>';}
