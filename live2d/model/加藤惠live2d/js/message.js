var home_Path = document.location.protocol +'//' + window.document.location.hostname +'/';

var userAgent = window.navigator.userAgent.toLowerCase();
console.log(userAgent);
var norunAI = [ "android", "iphone", "ipod", "ipad", "windows phone", "mqqbrowser" ,"msie","trident/7.0"];
var norunFlag = false;


for(var i=0;i<norunAI.length;i++){
	if(userAgent.indexOf(norunAI[i]) > -1){
		norunFlag = true;
		break;
	}
}

if(!window.WebGLRenderingContext){
	norunFlag = true;
}

if(!norunFlag){
	var hitFlag = false;
	var AIFadeFlag = false;
	var liveTlakTimer = null;
	var sleepTimer_ = null;
	var AITalkFlag = false;
	var talkNum = 0;
	(function (){
		function renderTip(template, context) {
			var tokenReg = /(\\)?\{([^\{\}\\]+)(\\)?\}/g;
			return template.replace(tokenReg, function (word, slash1, token, slash2) {
				if (slash1 || slash2) {
					return word.replace('\\', '');
				}
				var variables = token.replace(/\s/g, '').split('.');
				var currentObject = context;
				var i, length, variable;
				for (i = 0, length = variables.length; i < length; ++i) {
					variable = variables[i];
					currentObject = currentObject[variable];
					if (currentObject === undefined || currentObject === null) return '';
				}
				return currentObject;
			});
		}
		
		String.prototype.renderTip = function (context) {
			return renderTip(this, context);
		};
		
		var re = /x/;
		re.toString = function() {
			showMessage('哈哈，你打开了控制台，是想要看看我的秘密吗？', 5000);
			return '';
		};
		
		$(document).on('copy', function (){
			showMessage('你都复制了些什么呀，转载要记得加上出处哦~~', 5000);
		});
		
		function initTips(){
			$.ajax({
				cache: true,
				url: message_Path+'message.json',
				dataType: "json",
				success: function (result){
					$.each(result.mouseover, function (index, tips){
						$(tips.selector).mouseover(function (){
							var text = tips.text;
							if(Array.isArray(tips.text)) text = tips.text[Math.floor(Math.random() * tips.text.length + 1)-1];
							text = text.renderTip({text: $(this).text()});
							showMessage(text, 3000);
							talkValTimer();
							clearInterval(liveTlakTimer);
							liveTlakTimer = null;
						});
						$(tips.selector).mouseout(function (){
							showHitokoto();
							if(liveTlakTimer == null){
								liveTlakTimer = window.setInterval(function(){
									showHitokoto();
								},15000);
							};
						});
					});
					$.each(result.click, function (index, tips){
						$(tips.selector).click(function (){
							if(hitFlag){
								return false
							}
							hitFlag = true;
							setTimeout(function(){
								hitFlag = false;
							},8000);
							var text = tips.text;
							if(Array.isArray(tips.text)) text = tips.text[Math.floor(Math.random() * tips.text.length + 1)-1];
							text = text.renderTip({text: $(this).text()});
							showMessage(text, 3000);
						});
						clearInterval(liveTlakTimer);
						liveTlakTimer = null;
						if(liveTlakTimer == null){
							liveTlakTimer = window.setInterval(function(){
								showHitokoto();
							},15000);
						};
					});
				}
			});
		}
		initTips();
	
		var text;
		if(document.referrer !== ''){
			var referrer = document.createElement('a');
			referrer.href = document.referrer;
			text = '嗨！来自 <span style="color:#0099cc;">' + referrer.hostname + '</span> 的朋友！';
			var domain = referrer.hostname.split('.')[1];
			if (domain == 'baidu') {
				text = '嗨！ 来自 百度搜索 的朋友！<br>欢迎访问<span style="color:#0099cc;">「 ' + document.title.split(' - ')[0] + ' 」</span>';
			}else if (domain == 'so') {
				text = '嗨！ 来自 360搜索 的朋友！<br>欢迎访问<span style="color:#0099cc;">「 ' + document.title.split(' - ')[0] + ' 」</span>';
			}else if (domain == 'google') {
				text = '嗨！ 来自 谷歌搜索 的朋友！<br>欢迎访问<span style="color:#0099cc;">「 ' + document.title.split(' - ')[0] + ' 」</span>';
			}
		}else {
			if (window.location.href == home_Path) { //主页URL判断，需要斜杠结尾
				var now = (new Date()).getHours();
				if (now > 23 || now <= 5) {
					text = '你是夜猫子呀？这么晚还不睡觉，明天起的来嘛？';
				} else if (now > 5 && now <= 7) {
					text = '早上好！一日之计在于晨，美好的一天就要开始了！';
				} else if (now > 7 && now <= 11) {
					text = '上午好！工作顺利嘛，不要久坐，多起来走动走动哦！';
				} else if (now > 11 && now <= 14) {
					text = '中午了，工作了一个上午，现在是午餐时间！';
				} else if (now > 14 && now <= 17) {
					text = '午后很容易犯困呢，今天的运动目标完成了吗？';
				} else if (now > 17 && now <= 19) {
					text = '傍晚了！窗外夕阳的景色很美丽呢，最美不过夕阳红~~';
				} else if (now > 19 && now <= 21) {
					text = '晚上好，今天过得怎么样？';
				} else if (now > 21 && now <= 23) {
					text = '已经这么晚了呀，早点休息吧，晚安~~';
				} else {
					text = '嗨~ 快来逗我玩吧！';
				}
			}else {
				text = '欢迎阅读<span style="color:#0099cc;">「 ' + document.title.split(' - ')[0] + ' 」</span>';
			}
		}
		showMessage(text, 12000);
	})();
	
	liveTlakTimer = setInterval(function(){
		showHitokoto();
	},15000);
	
	function showHitokoto(){
		if(sessionStorage.getItem("Sleepy")!=="1"){
			if(!AITalkFlag){
				$.getJSON('https://sslapi.hitokoto.cn/',function(result){
					talkValTimer();
					showMessage(result.hitokoto, 0);
				});
			}
		}else{
			hideMessage(0);
			if(sleepTimer_==null){
				sleepTimer_ = setInterval(function(){
					checkSleep();
				},200);
			}
			console.log(sleepTimer_);
		}
	}
	
	function checkSleep(){
		var sleepStatu = sessionStorage.getItem("Sleepy");
		if(sleepStatu!=='1'){
			talkValTimer();
			showMessage('你回来啦~', 0);
			clearInterval(sleepTimer_);
			sleepTimer_= null;
		}
	}
	
	function showMessage(text, timeout){
		if(Array.isArray(text)) text = text[Math.floor(Math.random() * text.length + 1)-1];
		//console.log('showMessage', text);
		$('.message').stop();
		$('.message').html(text);
		$('.message').fadeTo(200, 1);
		//if (timeout === null) timeout = 5000;
		//hideMessage(timeout);
	}
	function talkValTimer(){
		$('#live_talk').val('1');
	}
	
	function hideMessage(timeout){
		//$('.message').stop().css('opacity',1);
		if (timeout === null) timeout = 5000;
		$('.message').delay(timeout).fadeTo(200, 0);
	}
	
	function initLive2d (){
		$('#hideButton').on('click', function(){
			if(AIFadeFlag){
				return false;
			}else{
				AIFadeFlag = true;
				localStorage.setItem("live2dhidden", "0");
				$('#landlord').fadeOut(200);
				$('#open_live2d').delay(200).fadeIn(200);
				setTimeout(function(){
					AIFadeFlag = false;
				},300);
			}
		});
		$('#open_live2d').on('click', function(){
			if(AIFadeFlag){
				return false;
			}else{
				AIFadeFlag = true;
				localStorage.setItem("live2dhidden", "1");
				$('#open_live2d').fadeOut(200);
				$('#landlord').delay(200).fadeIn(200);
				setTimeout(function(){
					AIFadeFlag = false;
				},300);
			}
		});
		$('#youduButton').on('click',function(){
			if($('#youduButton').hasClass('doudong')){
				var typeIs = $('#youduButton').attr('data-type');
				$('#youduButton').removeClass('doudong');
				$('body').removeClass(typeIs);
				$('#youduButton').attr('data-type','');
			}else{
				var duType = $('#duType').val();
				var duArr = duType.split(",");
				var dataType = duArr[Math.floor(Math.random() * duArr.length)];

				$('#youduButton').addClass('doudong');
				$('#youduButton').attr('data-type',dataType);
				$('body').addClass(dataType);
			}
		});
		if(talkAPI!==""){
			$('#showInfoBtn').on('click',function(){
				var live_statu = $('#live_statu_val').val();
				if(live_statu=="0"){
					return
				}else{
					$('#live_statu_val').val("0");
					$('.live_talk_input_body').fadeOut(500);
					AITalkFlag = false;
					showHitokoto();
					$('#showTalkBtn').show();
					$('#showInfoBtn').hide();
				}
			});
			$('#showTalkBtn').on('click',function(){
				var live_statu = $('#live_statu_val').val();
				if(live_statu=="1"){
					return
				}else{
					$('#live_statu_val').val("1");
					$('.live_talk_input_body').fadeIn(500);
					AITalkFlag = true;
					$('#showTalkBtn').hide();
					$('#showInfoBtn').show();
					
				}
			});
			$('#talk_send').on('click',function(){
				var info_ = $('#AIuserText').val();
				var userid_ = $('#AIuserName').val();
				if(info_ == "" ){
					showMessage('写点什么吧！',0);
					return;
				}
				if(userid_ == ""){
					showMessage('聊之前请告诉我你的名字吧！',0);
					return;
				}
				showMessage('思考中~', 0);
				$.ajax({
					type: 'POST',
					url: talkAPI,
					data: {
						"info":info_,
						"userid":userid_
					},
					success: function(res) {
						if(res.code !== 100000){
							talkValTimer();
							showMessage('似乎有什么错误，请和站长联系！',0);
						}else{
							talkValTimer();
							showMessage(res.text,0);
						}
						console.log(res);
						$('#AIuserText').val("");
						sessionStorage.setItem("live2duser", userid_);
					}
				});
			});
		}else{
			$('#showInfoBtn').hide();
			$('#showTalkBtn').hide();
			
		}
		//获取音乐信息初始化
		var bgmListInfo = $('input[name=live2dBGM]');
		if(bgmListInfo.length == 0){
			$('#musicButton').hide();
		}else{
			var bgmPlayNow = parseInt($('#live2d_bgm').attr('data-bgm'));
			var bgmPlayTime = 0;
			var live2dBGM_Num = sessionStorage.getItem("live2dBGM_Num");
			var live2dBGM_PlayTime = sessionStorage.getItem("live2dBGM_PlayTime");
			if(live2dBGM_Num){
				if(live2dBGM_Num<=$('input[name=live2dBGM]').length-1){
					bgmPlayNow = parseInt(live2dBGM_Num);
				}
			}
			if(live2dBGM_PlayTime){
				bgmPlayTime = parseInt(live2dBGM_PlayTime);
			}
			var live2dBGMSrc = bgmListInfo.eq(bgmPlayNow).val();
			$('#live2d_bgm').attr('data-bgm',bgmPlayNow);
			$('#live2d_bgm').attr('src',live2dBGMSrc);
			$('#live2d_bgm')[0].currentTime = bgmPlayTime;
			$('#live2d_bgm')[0].volume = 0.5;
			var live2dBGM_IsPlay = sessionStorage.getItem("live2dBGM_IsPlay");
			var live2dBGM_WindowClose = sessionStorage.getItem("live2dBGM_WindowClose");
			if(live2dBGM_IsPlay == '0' && live2dBGM_WindowClose == '0'){
				$('#live2d_bgm')[0].play();
				$('#musicButton').addClass('play');
			}
			sessionStorage.setItem("live2dBGM_WindowClose" , '1');
			$('#musicButton').on('click',function(){
				if($('#musicButton').hasClass('play')){
					$('#live2d_bgm')[0].pause();
					$('#musicButton').removeClass('play');
					sessionStorage.setItem("live2dBGM_IsPlay",'1');
				}else{
					$('#live2d_bgm')[0].play();
					$('#musicButton').addClass('play');
					sessionStorage.setItem("live2dBGM_IsPlay",'0');
				}
			});
			window.onbeforeunload = function(){ 
			 	sessionStorage.setItem("live2dBGM_WindowClose" , '0');
				if($('#musicButton').hasClass('play')){
					sessionStorage.setItem("live2dBGM_IsPlay",'0');
				}
			} 
			document.getElementById('live2d_bgm').addEventListener("timeupdate", function(){
				var live2dBgmPlayTimeNow = document.getElementById('live2d_bgm').currentTime;
				sessionStorage.setItem("live2dBGM_PlayTime" , live2dBgmPlayTimeNow );
			});
			document.getElementById('live2d_bgm').addEventListener("ended", function(){
				var listNow = parseInt($('#live2d_bgm').attr('data-bgm'));
				listNow ++ ;
				if(listNow > $('input[name=live2dBGM]').length-1){
					listNow = 0;
				}
				var listNewSrc = $('input[name=live2dBGM]').eq(listNow).val();
				sessionStorage.setItem("live2dBGM_Num",listNow);
				$('#live2d_bgm').attr('src',listNewSrc);
				$('#live2d_bgm')[0].play();
				$('#live2d_bgm').attr('data-bgm',listNow);
			});
			document.getElementById('live2d_bgm').addEventListener("error", function(){
				$('#live2d_bgm')[0].pause();
				$('#musicButton').removeClass('play');
				showMessage('音乐似乎加载不出来了呢！',0);
			});
		}
		//获取用户名
		var live2dUser = sessionStorage.getItem("live2duser");
		if(live2dUser !== null){
			$('#AIuserName').val(live2dUser);
		}
		//获取位置
		var landL = sessionStorage.getItem("historywidth");
		var landB = sessionStorage.getItem("historyheight");
		if(landL == null || landB ==null){
			landL = '5px'
			landB = '0px'
		}
		$('#landlord').css('left',landL+'px');
		$('#landlord').css('bottom',landB + 'px');
		//移动
		function getEvent() {
			return window.event || arguments.callee.caller.arguments[0];
		}
		var smcc = document.getElementById("landlord");
		var moveX = 0;
		var moveY = 0;
		var moveBottom = 0;
		var moveLeft = 0;
		var moveable = false;
		var docMouseMoveEvent = document.onmousemove;
		var docMouseUpEvent = document.onmouseup;
		smcc.onmousedown = function(){
			var ent = getEvent();
			moveable = true;
			moveX = ent.clientX;
			moveY = ent.clientY;
			var obj = smcc;
			moveBottom = parseInt(obj.style.bottom);
			moveLeft = parseInt(obj.style.left);
			if(isFirefox=navigator.userAgent.indexOf("Firefox")>0){
				window.getSelection().removeAllRanges();
			}			
			document.onmousemove = function(){
				if(moveable){
					var ent = getEvent();
					var x = moveLeft + ent.clientX - moveX;
					var y = moveBottom +  (moveY - ent.clientY);
					obj.style.left = x + "px";
					obj.style.bottom = y + "px";
				}
			};
			document.onmouseup = function(){
				if(moveable){
					var historywidth = obj.style.left;
					var historyheight = obj.style.bottom;
					historywidth = historywidth.replace('px', '');
					historyheight = historyheight.replace('px', '');
					sessionStorage.setItem("historywidth", historywidth);
					sessionStorage.setItem("historyheight", historyheight);
					document.onmousemove = docMouseMoveEvent;
					document.onmouseup = docMouseUpEvent;
					moveable = false; 
					moveX = 0;
					moveY = 0;
					moveBottom = 0;
					moveLeft = 0;
				}
			};
		};
	}
	$(document).ready(function() {
		var AIimgSrc = [
			home_Path + message_Path + "model/katou_01/moc/katou.2048/texture_00.png"
		]
		var images = [];
		var imgLength = AIimgSrc.length;
		var loadingNum = 0;
		for(var i=0;i<imgLength;i++){
			images[i] = new Image();
			images[i].src = AIimgSrc[i];
			images[i].onload = function(){
				loadingNum++;
				if(loadingNum===imgLength){
					var live2dhidden = localStorage.getItem("live2dhidden");
					if(live2dhidden==="0"){
						setTimeout(function(){
							$('#open_live2d').fadeIn(200);
						},1300);
					}else{
						setTimeout(function(){
							$('#landlord').fadeIn(200);
						},1300);
					}
					setTimeout(function(){
						loadlive2d("live2d", message_Path+"model/katou_01/katou_01.model.json");
					},1000);
					initLive2d ();
					images = null;
				}
			}
		}
	});
}
