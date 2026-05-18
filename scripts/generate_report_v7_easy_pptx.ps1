param(
    [string]$DocxPath = "C:\Users\user\Downloads\SDACS_Final_Report_v7_Easy.docx",
    [string]$OutputPath = "docs/presentation/SDACS_Final_Report_v7_Easy_Based.pptx"
)

$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$OutFile = Join-Path $RepoRoot $OutputPath
$BuildRoot = Join-Path $RepoRoot ".tmp_report_v7_easy_pptx"
$ExtractedMedia = Join-Path $BuildRoot "source_media"

function Assert-InRepo([string]$Path) {
    $full = [System.IO.Path]::GetFullPath($Path)
    if (-not $full.StartsWith($RepoRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to write outside repository: $full"
    }
    return $full
}

Assert-InRepo $OutFile | Out-Null
Assert-InRepo $BuildRoot | Out-Null

if (-not (Test-Path $DocxPath)) {
    throw "DOCX not found: $DocxPath"
}

if (Test-Path $BuildRoot) {
    Remove-Item -LiteralPath $BuildRoot -Recurse -Force
}

$dirs = @(
    "_rels", "docProps", "ppt", "ppt/_rels", "ppt/slides", "ppt/slides/_rels",
    "ppt/slideMasters", "ppt/slideMasters/_rels", "ppt/slideLayouts",
    "ppt/slideLayouts/_rels", "ppt/theme", "ppt/media", "source_media"
)
foreach ($d in $dirs) {
    New-Item -ItemType Directory -Force -Path (Join-Path $BuildRoot $d) | Out-Null
}

function Write-Utf8([string]$RelativePath, [string]$Content) {
    $path = Join-Path $BuildRoot $RelativePath
    $dir = Split-Path $path -Parent
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
    }
    Set-Content -LiteralPath $path -Value $Content -Encoding UTF8
}

function E([string]$Text) {
    if ($null -eq $Text) { return "" }
    return [System.Security.SecurityElement]::Escape($Text)
}

function Emu([double]$Inches) {
    return [int64][Math]::Round($Inches * 914400)
}

function FillXml([string]$Color, [int]$Transparency = 0) {
    $alpha = [Math]::Max(0, [Math]::Min(100000, (100 - $Transparency) * 1000))
    if ($Transparency -gt 0) {
        return "<a:solidFill><a:srgbClr val=`"$Color`"><a:alpha val=`"$alpha`"/></a:srgbClr></a:solidFill>"
    }
    return "<a:solidFill><a:srgbClr val=`"$Color`"/></a:solidFill>"
}

function TextRuns([string]$Text, [int]$FontSize, [string]$Color, [bool]$Bold, [string]$Align) {
    $size = $FontSize * 100
    $boldAttr = if ($Bold) { " b=`"1`"" } else { "" }
    $paras = New-Object System.Collections.Generic.List[string]
    foreach ($line in ($Text -split "`n", -1)) {
        $escaped = E $line
        $paras.Add("<a:p><a:pPr algn=`"$Align`"/><a:r><a:rPr lang=`"ko-KR`" sz=`"$size`"$boldAttr><a:solidFill><a:srgbClr val=`"$Color`"/></a:solidFill><a:latin typeface=`"Malgun Gothic`"/><a:ea typeface=`"Malgun Gothic`"/><a:cs typeface=`"Malgun Gothic`"/></a:rPr><a:t>$escaped</a:t></a:r><a:endParaRPr lang=`"ko-KR`" sz=`"$size`"/></a:p>")
    }
    return ($paras -join "")
}

function TextBox([int]$Id, [double]$X, [double]$Y, [double]$W, [double]$H, [string]$Text, [int]$FontSize = 24, [string]$Color = "FFFFFF", [bool]$Bold = $false, [string]$Align = "ctr", [string]$Fill = "", [int]$Transparency = 0) {
    $xemu = Emu $X
    $yemu = Emu $Y
    $wemu = Emu $W
    $hemu = Emu $H
    $fill = if ($Fill) { FillXml $Fill $Transparency } else { "<a:noFill/>" }
    $paras = TextRuns $Text $FontSize $Color $Bold $Align
    return @"
<p:sp>
  <p:nvSpPr><p:cNvPr id="$Id" name="Text $Id"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
  <p:spPr><a:xfrm><a:off x="$xemu" y="$yemu"/><a:ext cx="$wemu" cy="$hemu"/></a:xfrm><a:prstGeom prst="roundRect"><a:avLst/></a:prstGeom>$fill<a:ln><a:noFill/></a:ln></p:spPr>
  <p:txBody><a:bodyPr wrap="square" anchor="mid" lIns="91440" tIns="45720" rIns="91440" bIns="45720"/><a:lstStyle/>$paras</p:txBody>
</p:sp>
"@
}

function Rect([int]$Id, [double]$X, [double]$Y, [double]$W, [double]$H, [string]$Fill, [int]$Transparency = 0) {
    $xemu = Emu $X
    $yemu = Emu $Y
    $wemu = Emu $W
    $hemu = Emu $H
    return @"
<p:sp>
  <p:nvSpPr><p:cNvPr id="$Id" name="Shape $Id"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
  <p:spPr><a:xfrm><a:off x="$xemu" y="$yemu"/><a:ext cx="$wemu" cy="$hemu"/></a:xfrm><a:prstGeom prst="roundRect"><a:avLst/></a:prstGeom>$(FillXml $Fill $Transparency)<a:ln><a:noFill/></a:ln></p:spPr>
</p:sp>
"@
}

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

$fs = [System.IO.File]::Open($DocxPath, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
$docZip = [System.IO.Compression.ZipArchive]::new($fs, [System.IO.Compression.ZipArchiveMode]::Read)
try {
    foreach ($entry in $docZip.Entries | Where-Object { $_.FullName -like "word/media/*" }) {
        $target = Join-Path $ExtractedMedia ([System.IO.Path]::GetFileName($entry.FullName))
        [System.IO.Compression.ZipFileExtensions]::ExtractToFile($entry, $target, $true)
    }
}
finally {
    $docZip.Dispose()
    $fs.Dispose()
}

$script:MediaCounter = 1
function Picture([int]$Id, [double]$X, [double]$Y, [double]$W, [double]$H, [string]$ImageName, [System.Collections.Generic.List[object]]$Rels) {
    $source = Join-Path $ExtractedMedia $ImageName
    if (-not (Test-Path $source)) {
        return TextBox $Id $X $Y $W $H "보고서 이미지 없음`n$ImageName" 14 "64748B" $false "ctr" "E2E8F0"
    }
    $mediaName = "image$script:MediaCounter.png"
    $script:MediaCounter++
    Copy-Item -LiteralPath $source -Destination (Join-Path $BuildRoot "ppt/media/$mediaName") -Force
    $relId = "rId$($Rels.Count + 2)"
    $Rels.Add([pscustomobject]@{ Id = $relId; Target = "../media/$mediaName"; Type = "image" })
    $xemu = Emu $X
    $yemu = Emu $Y
    $wemu = Emu $W
    $hemu = Emu $H
    return @"
<p:pic>
  <p:nvPicPr><p:cNvPr id="$Id" name="Picture $Id"/><p:cNvPicPr/><p:nvPr/></p:nvPicPr>
  <p:blipFill><a:blip r:embed="$relId"/><a:stretch><a:fillRect/></a:stretch></p:blipFill>
  <p:spPr><a:xfrm><a:off x="$xemu" y="$yemu"/><a:ext cx="$wemu" cy="$hemu"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr>
</p:pic>
"@
}

function SlideXml([object[]]$Shapes) {
    $shapeXml = ($Shapes -join "`n")
    return @"
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>$shapeXml</p:spTree></p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sld>
"@
}

function SlideRelsXml([System.Collections.Generic.List[object]]$Rels) {
    $parts = New-Object System.Collections.Generic.List[string]
    $parts.Add('<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>')
    foreach ($r in $Rels) {
        $parts.Add("<Relationship Id=`"$($r.Id)`" Type=`"http://schemas.openxmlformats.org/officeDocument/2006/relationships/image`" Target=`"$($r.Target)`"/>")
    }
    return "<?xml version=`"1.0`" encoding=`"UTF-8`" standalone=`"yes`"?><Relationships xmlns=`"http://schemas.openxmlformats.org/package/2006/relationships`">$($parts -join '')</Relationships>"
}

function NewSlide([int]$Index, [scriptblock]$Builder) {
    $rels = New-Object System.Collections.Generic.List[object]
    $shapes = & $Builder $rels
    Write-Utf8 "ppt/slides/slide$Index.xml" (SlideXml $shapes)
    Write-Utf8 "ppt/slides/_rels/slide$Index.xml.rels" (SlideRelsXml $rels)
}

$C = @{
    Dark = "07111F"; Navy = "0E2438"; Blue = "1C6EA4"; Cyan = "00A8D8";
    Green = "16A34A"; Orange = "F97316"; Red = "DC2626"; Yellow = "FBBF24";
    White = "FFFFFF"; Off = "F8FAFC"; Ink = "111827"; Muted = "64748B";
    Pale = "E2E8F0"; SoftBlue = "DBEAFE"; SoftGreen = "DCFCE7"; SoftOrange = "FFEDD5";
}

NewSlide 1 { param($rels) @(
    Rect 2 0 0 13.333 7.5 $C.Dark
    TextBox 3 0.75 0.72 11.8 0.9 "SDACS" 58 $C.Cyan $true "ctr"
    TextBox 4 1.0 1.8 11.3 0.55 "Swarm Drone Airspace Control Automation System" 22 $C.Pale $false "ctr"
    TextBox 5 1.25 2.75 10.8 1.2 "여러 대의 드론이 스스로`n하늘길을 관리하는 시스템" 38 $C.White $true "ctr"
    TextBox 6 1.45 4.65 10.45 0.6 "비전공자 일반인을 위한 쉬운 설명 버전 기반 PPT" 18 "CBD5E1" $false "ctr"
    TextBox 7 1.45 5.55 10.45 0.45 "국립목포대학교 드론기계공학과 · 장선우 · 2026" 15 "CBD5E1" $false "ctr"
) }

NewSlide 2 { param($rels) @(
    Rect 2 0 0 13.333 7.5 $C.Off
    TextBox 3 0.65 0.45 12.0 0.65 "한 줄 요약" 32 $C.Ink $true "ctr"
    TextBox 4 0.85 1.25 5.3 1.6 "하늘의`n자율 교통경찰" 40 $C.Blue $true "ctr" $C.SoftBlue
    Picture 5 6.75 1.05 5.65 4.25 "image1.png" $rels
    TextBox 6 0.95 3.35 5.1 1.4 "드론끼리 자동으로 충돌을 피하게 만드는 시스템" 26 $C.Ink $true "ctr"
    TextBox 7 1.1 5.35 10.9 0.45 "기체보다 중요한 것은 하늘길을 관리하는 소프트웨어입니다." 17 $C.Muted $false "ctr"
) }

NewSlide 3 { param($rels) @(
    Rect 2 0 0 13.333 7.5 $C.Off
    TextBox 3 0.65 0.35 12.0 0.65 "왜 필요한가 — 하늘길이 막히고 있습니다" 30 $C.Ink $true "ctr"
    Picture 4 0.75 1.2 5.85 3.0 "image2.png" $rels
    Picture 5 6.75 1.2 5.85 3.0 "image3.png" $rels
    TextBox 6 1.0 4.75 11.35 1.35 "드론 90만 대가 낮은 하늘을 함께 쓰지만, 작은 드론은 기존 항공 관제망에서 놓치기 쉽습니다." 25 $C.Ink $true "ctr" $C.SoftOrange
    TextBox 7 1.2 6.35 10.9 0.35 "보고서 표현: 골목길에는 차가 넘치는데 큰길 신호등만 있는 상황" 15 $C.Muted $false "ctr"
) }

NewSlide 4 { param($rels) @(
    Rect 2 0 0 13.333 7.5 $C.Navy
    TextBox 3 0.7 0.55 12.0 0.65 "기존 방식의 한계" 34 $C.White $true "ctr"
    TextBox 4 0.9 1.55 3.75 3.6 "중앙 서버`n`n한 곳이 멈추면`n전체가 흔들림" 25 $C.Ink $true "ctr" $C.SoftOrange
    TextBox 5 4.8 1.55 3.75 3.6 "드론쇼 방식`n`n미리 짠 길만 따라가서`n돌발 상황에 약함" 24 $C.Ink $true "ctr" $C.SoftBlue
    TextBox 6 8.7 1.55 3.75 3.6 "고정 인프라`n`n사각지대와 설치 부담이 큼" 24 $C.Ink $true "ctr" $C.SoftGreen
    TextBox 7 1.2 6.0 10.9 0.55 "SDACS는 중앙에만 묻는 방식이 아니라, 드론들이 서로 소통하는 방식을 지향합니다." 17 $C.Pale $false "ctr"
) }

NewSlide 5 { param($rels) @(
    Rect 2 0 0 13.333 7.5 $C.Off
    TextBox 3 0.65 0.4 12.0 0.65 "핵심 아이디어 — 드론이 직접 감시망이 된다" 30 $C.Ink $true "ctr"
    Picture 4 0.85 1.15 5.7 4.25 "image4.png" $rels
    TextBox 5 7.0 1.45 5.2 1.0 "땅에 레이더를 설치하지 말고" 28 $C.Muted $true "ctr"
    TextBox 6 7.0 2.65 5.2 1.1 "드론 20대가 하늘에 올라가" 30 $C.Blue $true "ctr"
    TextBox 7 7.0 3.9 5.2 1.1 "직접 감시망이 되자" 34 $C.Orange $true "ctr"
    TextBox 8 1.1 6.35 11.1 0.35 "보고서 비유: 고정 CCTV 대신 공중 경비원 20명이 무전기로 소통하는 방식" 15 $C.Muted $false "ctr"
) }

NewSlide 6 { param($rels) @(
    Rect 2 0 0 13.333 7.5 $C.Off
    TextBox 3 0.65 0.4 12.0 0.65 "시스템 구조 — 4층짜리 건물처럼 역할 분담" 30 $C.Ink $true "ctr"
    Picture 4 0.85 1.15 6.2 4.7 "image5.png" $rels
    TextBox 5 7.45 1.25 4.9 0.9 "현장" 24 $C.Ink $true "ctr" $C.SoftBlue
    TextBox 6 7.45 2.25 4.9 0.9 "지휘" 24 $C.Ink $true "ctr" $C.SoftGreen
    TextBox 7 7.45 3.25 4.9 0.9 "두뇌" 24 $C.Ink $true "ctr" $C.SoftOrange
    TextBox 8 7.45 4.25 4.9 0.9 "사용자 화면" 24 $C.Ink $true "ctr" "FEE2E2"
    TextBox 9 1.2 6.25 10.9 0.45 "회사 조직처럼 각 층이 역할을 나눠 맡고 서로 받쳐줍니다." 17 $C.Muted $false "ctr"
) }

NewSlide 7 { param($rels) @(
    Rect 2 0 0 13.333 7.5 $C.Dark
    TextBox 3 0.65 0.4 12.0 0.7 "충돌을 막는 방법 — 5겹 안전망" 34 $C.Yellow $true "ctr"
    Picture 4 0.75 1.25 5.85 3.6 "image6.png" $rels
    Picture 5 6.75 1.25 5.85 3.6 "image7.png" $rels
    TextBox 6 1.1 5.45 11.1 0.75 "자동차의 안전벨트·에어백·ABS처럼, 여러 장치가 순서대로 작동합니다." 24 $C.White $true "ctr"
    TextBox 7 1.3 6.35 10.7 0.35 "하나가 놓쳐도 다음 장치가 위험을 줄이는 다중 안전망 원리" 14 "CBD5E1" $false "ctr"
) }

NewSlide 8 { param($rels) @(
    Rect 2 0 0 13.333 7.5 $C.Off
    TextBox 3 0.65 0.35 12.0 0.65 "연구 방법 — 왜 스타크래프트인가" 31 $C.Ink $true "ctr"
    Picture 4 0.75 1.1 5.85 3.45 "image8.png" $rels
    Picture 5 6.75 1.1 5.85 3.45 "image9.png" $rels
    TextBox 6 1.0 5.15 11.35 1.0 "수십 개 유닛을 동시에 지휘하는 게임은 드론 군집 제어 연구의 좋은 실험장입니다." 25 $C.Ink $true "ctr" $C.SoftBlue
    TextBox 7 1.2 6.35 10.9 0.35 "보고서 핵심 질문: 게임 AI의 군집 제어 능력을 실제 드론 관제로 옮길 수 있을까?" 14 $C.Muted $false "ctr"
) }

NewSlide 9 { param($rels) @(
    Rect 2 0 0 13.333 7.5 $C.Navy
    TextBox 3 0.65 0.4 12.0 0.65 "불법 드론 쫓아내기 — 1초 이내 자동 대응" 30 $C.White $true "ctr"
    Picture 4 0.95 1.2 5.9 4.35 "image10.png" $rels
    TextBox 5 7.35 1.35 4.75 0.9 "탐지" 24 $C.Ink $true "ctr" $C.SoftBlue
    TextBox 6 7.35 2.35 4.75 0.9 "식별" 24 $C.Ink $true "ctr" $C.SoftGreen
    TextBox 7 7.35 3.35 4.75 0.9 "경고" 24 $C.Ink $true "ctr" $C.SoftOrange
    TextBox 8 7.35 4.35 4.75 0.9 "퇴각 유도" 24 $C.Ink $true "ctr" "FEE2E2"
    TextBox 9 1.2 6.25 10.9 0.45 "눈을 한 번 깜빡이면 이미 대응 흐름이 끝나는 수준을 목표로 합니다." 17 $C.Pale $false "ctr"
) }

NewSlide 10 { param($rels) @(
    Rect 2 0 0 13.333 7.5 $C.Off
    TextBox 3 0.65 0.45 12.0 0.65 "관제사 화면 — 조종석에 앉은 것처럼" 31 $C.Ink $true "ctr"
    TextBox 4 0.85 1.35 3.8 3.5 "3D 지도`n`n드론 색상 표시`n상태 한눈에 확인" 24 $C.Ink $true "ctr" $C.SoftBlue
    TextBox 5 4.85 1.35 3.8 3.5 "브라우저 하나`n`n별도 설치 없이`n어디서나 접근" 24 $C.Ink $true "ctr" $C.SoftGreen
    TextBox 6 8.85 1.35 3.6 3.5 "AI 비서`n`n자연어 명령을`n즉시 실행" 24 $C.Ink $true "ctr" $C.SoftOrange
    TextBox 7 1.0 5.65 11.35 0.8 "보고서 표현: 게임 콘솔과 비행기 조종석을 합친 느낌의 통합 조종석" 24 $C.Ink $true "ctr"
) }

NewSlide 11 { param($rels) @(
    Rect 2 0 0 13.333 7.5 $C.Off
    TextBox 3 0.65 0.35 12.0 0.65 "성능 증명 — 38,400번 실험이 말한다" 31 $C.Ink $true "ctr"
    Picture 4 0.85 1.15 5.9 4.25 "image11.png" $rels
    TextBox 5 7.25 1.25 4.75 1.0 "38,400번" 38 $C.Blue $true "ctr"
    TextBox 6 7.25 2.35 4.75 0.65 "컴퓨터 반복 실험" 22 $C.Ink $true "ctr"
    TextBox 7 7.25 3.35 4.75 1.0 "2,668개" 38 $C.Orange $true "ctr"
    TextBox 8 7.25 4.45 4.75 0.65 "자동 테스트 통과" 22 $C.Ink $true "ctr"
    TextBox 9 1.2 6.25 10.9 0.45 "보고서 v7 기준 수치로 구성했습니다." 16 $C.Muted $false "ctr"
) }

NewSlide 12 { param($rels) @(
    Rect 2 0 0 13.333 7.5 $C.Navy
    TextBox 3 0.65 0.5 12.0 0.7 "63가지 상황 실제 테스트" 36 $C.White $true "ctr"
    TextBox 4 1.0 1.55 3.4 3.1 "63개 상황" 34 $C.Ink $true "ctr" $C.SoftBlue
    TextBox 5 4.95 1.55 3.4 3.1 "316번 실행" 34 $C.Ink $true "ctr" $C.SoftGreen
    TextBox 6 8.9 1.55 3.4 3.1 "평균 96.9%" 34 $C.Ink $true "ctr" $C.SoftOrange
    TextBox 7 1.1 5.35 11.1 0.8 "기본 상황부터 태풍, 불법침입, 군사작전까지 조건을 나눠 검증했습니다." 24 $C.Pale $true "ctr"
    TextBox 8 1.2 6.35 10.9 0.35 "7대 광역시 도시 환경에서도 21개 상황 모두 98% 이상으로 보고서에 정리됨" 14 "CBD5E1" $false "ctr"
) }

NewSlide 13 { param($rels) @(
    Rect 2 0 0 13.333 7.5 $C.Off
    TextBox 3 0.65 0.45 12.0 0.65 "광주광역시 실증 전략" 34 $C.Ink $true "ctr"
    TextBox 4 1.1 1.45 11.1 0.9 "광주를 드론 군집 관제 실증 도시로" 30 $C.Blue $true "ctr" $C.SoftBlue
    TextBox 5 1.1 2.75 3.35 2.0 "AI 도시" 26 $C.Ink $true "ctr" $C.SoftGreen
    TextBox 6 4.95 2.75 3.35 2.0 "5G·CCTV 인프라" 25 $C.Ink $true "ctr" $C.SoftOrange
    TextBox 7 8.8 2.75 3.35 2.0 "인구 150만`n도시 규모" 24 $C.Ink $true "ctr" "FEE2E2"
    TextBox 8 1.1 5.75 11.1 0.65 "보고서 v6 보완: 광주 3개 상황 모두 98% 이상, 실제 실증 전 컴퓨터 검증 완료" 19 $C.Muted $false "ctr"
) }

NewSlide 14 { param($rels) @(
    Rect 2 0 0 13.333 7.5 $C.Off
    TextBox 3 0.65 0.45 12.0 0.65 "어디에 쓸 수 있는가" 34 $C.Ink $true "ctr"
    TextBox 4 0.85 1.35 2.8 3.5 "택배" 29 $C.Ink $true "ctr" $C.SoftBlue
    TextBox 5 3.85 1.35 2.8 3.5 "재난 대응" 29 $C.Ink $true "ctr" $C.SoftGreen
    TextBox 6 6.85 1.35 2.8 3.5 "국방" 29 $C.Ink $true "ctr" $C.SoftOrange
    TextBox 7 9.85 1.35 2.65 3.5 "의료 수송" 28 $C.Ink $true "ctr" "FEE2E2"
    TextBox 8 1.2 5.65 10.9 0.75 "드론이 쓰이는 거의 모든 분야에 적용 가능한 하늘 교통 운영 기술입니다." 24 $C.Ink $true "ctr"
) }

NewSlide 15 { param($rels) @(
    Rect 2 0 0 13.333 7.5 $C.Off
    TextBox 3 0.65 0.35 12.0 0.65 "개발 로드맵" 34 $C.Ink $true "ctr"
    Picture 4 1.1 1.1 11.1 4.4 "image12.png" $rels
    TextBox 5 1.2 6.0 10.9 0.55 "캡스톤 디자인 16주로 시작해, 장기적으로 여러 도시 적용을 목표로 합니다." 18 $C.Muted $false "ctr"
) }

NewSlide 16 { param($rels) @(
    Rect 2 0 0 13.333 7.5 $C.Off
    TextBox 3 0.65 0.35 12.0 0.65 "특허 관계도와 출원 전략" 31 $C.Ink $true "ctr"
    Picture 4 0.85 1.1 5.85 4.25 "image13.png" $rels
    Picture 5 6.75 1.1 5.85 4.25 "image14.png" $rels
    TextBox 6 1.15 6.05 11.0 0.55 "보고서 결론: 공개·논문·GitHub 이전에 가출원으로 날짜 확보가 중요합니다." 18 $C.Muted $false "ctr"
) }

NewSlide 17 { param($rels) @(
    Rect 2 0 0 13.333 7.5 $C.Dark
    TextBox 3 0.85 0.85 11.65 0.85 "결론 — 하늘길의 혁명" 40 $C.Yellow $true "ctr"
    TextBox 4 1.2 2.0 10.9 1.3 '"드론이 직접 레이더가 되어 스스로 협력한다"' 34 $C.White $true "ctr"
    TextBox 5 1.35 3.75 10.65 0.9 "이 한 가지 발상이 드론 관제의 미래를 바꿉니다." 28 $C.Pale $true "ctr"
    Picture 6 3.6 5.05 6.1 1.5 "image15.png" $rels
    TextBox 7 1.2 6.78 10.9 0.25 "Based on SDACS_Final_Report_v7_Easy.docx" 11 "CBD5E1" $false "ctr"
) }

$slideCount = 17
$slideOverrides = New-Object System.Collections.Generic.List[string]
for ($i = 1; $i -le $slideCount; $i++) {
    $slideOverrides.Add("<Override PartName=`"/ppt/slides/slide$i.xml`" ContentType=`"application/vnd.openxmlformats-officedocument.presentationml.slide+xml`"/>")
}

Write-Utf8 "[Content_Types].xml" @"
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Default Extension="png" ContentType="image/png"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
  <Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>
  <Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>
  <Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>
  $($slideOverrides -join "`n  ")
</Types>
"@

Write-Utf8 "_rels/.rels" @"
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>
"@

$slideIds = New-Object System.Collections.Generic.List[string]
$presRels = New-Object System.Collections.Generic.List[string]
$presRels.Add('<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>')
for ($i = 1; $i -le $slideCount; $i++) {
    $rid = $i + 1
    $sid = 255 + $i
    $slideIds.Add("<p:sldId id=`"$sid`" r:id=`"rId$rid`"/>")
    $presRels.Add("<Relationship Id=`"rId$rid`" Type=`"http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide`" Target=`"slides/slide$i.xml`"/>")
}

Write-Utf8 "ppt/presentation.xml" @"
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst>
  <p:sldIdLst>$($slideIds -join '')</p:sldIdLst>
  <p:sldSz cx="12192000" cy="6858000" type="wide"/>
  <p:notesSz cx="6858000" cy="9144000"/>
  <p:defaultTextStyle><a:defPPr><a:defRPr lang="ko-KR"/></a:defPPr></p:defaultTextStyle>
</p:presentation>
"@

Write-Utf8 "ppt/_rels/presentation.xml.rels" "<?xml version=`"1.0`" encoding=`"UTF-8`" standalone=`"yes`"?><Relationships xmlns=`"http://schemas.openxmlformats.org/package/2006/relationships`">$($presRels -join '')</Relationships>"

Write-Utf8 "ppt/slideMasters/slideMaster1.xml" @"
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld>
  <p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>
  <p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst>
  <p:txStyles><p:titleStyle/><p:bodyStyle/><p:otherStyle/></p:txStyles>
</p:sldMaster>
"@

Write-Utf8 "ppt/slideMasters/_rels/slideMaster1.xml.rels" @"
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/>
</Relationships>
"@

Write-Utf8 "ppt/slideLayouts/slideLayout1.xml" @"
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" type="blank" preserve="1">
  <p:cSld name="Blank"><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sldLayout>
"@

Write-Utf8 "ppt/slideLayouts/_rels/slideLayout1.xml.rels" @"
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/>
</Relationships>
"@

Write-Utf8 "ppt/theme/theme1.xml" @"
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="SDACS Report V7 Easy">
  <a:themeElements>
    <a:clrScheme name="SDACS"><a:dk1><a:srgbClr val="111827"/></a:dk1><a:lt1><a:srgbClr val="FFFFFF"/></a:lt1><a:dk2><a:srgbClr val="0E2438"/></a:dk2><a:lt2><a:srgbClr val="F8FAFC"/></a:lt2><a:accent1><a:srgbClr val="1C6EA4"/></a:accent1><a:accent2><a:srgbClr val="16A34A"/></a:accent2><a:accent3><a:srgbClr val="F97316"/></a:accent3><a:accent4><a:srgbClr val="FBBF24"/></a:accent4><a:accent5><a:srgbClr val="00A8D8"/></a:accent5><a:accent6><a:srgbClr val="DC2626"/></a:accent6><a:hlink><a:srgbClr val="1C6EA4"/></a:hlink><a:folHlink><a:srgbClr val="64748B"/></a:folHlink></a:clrScheme>
    <a:fontScheme name="Malgun Gothic"><a:majorFont><a:latin typeface="Malgun Gothic"/><a:ea typeface="Malgun Gothic"/><a:cs typeface="Malgun Gothic"/></a:majorFont><a:minorFont><a:latin typeface="Malgun Gothic"/><a:ea typeface="Malgun Gothic"/><a:cs typeface="Malgun Gothic"/></a:minorFont></a:fontScheme>
    <a:fmtScheme name="SDACS"><a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:fillStyleLst><a:lnStyleLst><a:ln w="6350"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln></a:lnStyleLst><a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst><a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst></a:fmtScheme>
  </a:themeElements>
</a:theme>
"@

Write-Utf8 "docProps/core.xml" @"
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>SDACS Final Report v7 Easy Based Presentation</dc:title>
  <dc:subject>군집드론 공역통제 자동화 시스템</dc:subject>
  <dc:creator>SDACS Capstone Team</dc:creator>
  <cp:lastModifiedBy>Codex</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">2026-05-08T00:00:00Z</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">2026-05-08T00:00:00Z</dcterms:modified>
</cp:coreProperties>
"@

Write-Utf8 "docProps/app.xml" @"
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>SDACS OpenXML Generator</Application>
  <PresentationFormat>On-screen Show (16:9)</PresentationFormat>
  <Slides>$slideCount</Slides>
  <Company>Capstone Team 3</Company>
</Properties>
"@

$outDir = Split-Path $OutFile -Parent
if (-not (Test-Path $outDir)) {
    New-Item -ItemType Directory -Force -Path $outDir | Out-Null
}
if (Test-Path $OutFile) {
    Remove-Item -LiteralPath $OutFile -Force
}

$zipStream = [System.IO.File]::Open($OutFile, [System.IO.FileMode]::Create)
$zip = [System.IO.Compression.ZipArchive]::new($zipStream, [System.IO.Compression.ZipArchiveMode]::Create)
try {
    Get-ChildItem -LiteralPath $BuildRoot -Recurse -File | Where-Object { $_.FullName -notlike "$ExtractedMedia*" } | ForEach-Object {
        $entryName = $_.FullName.Substring($BuildRoot.Length).TrimStart("\", "/").Replace("\", "/")
        [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $_.FullName, $entryName, [System.IO.Compression.CompressionLevel]::Optimal) | Out-Null
    }
}
finally {
    $zip.Dispose()
    $zipStream.Dispose()
}

Remove-Item -LiteralPath $BuildRoot -Recurse -Force
Write-Host "Created $OutFile"

