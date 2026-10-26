let accountState=null;
const accountEl=id=>document.getElementById(id);
function applyAccount(user){
 accountState=user;
 const name=user.display_name||user.username;
 document.documentElement.dataset.textSize=user.font_size||'large';
 accountEl('account-name').textContent=name;
 accountEl('account-avatar').textContent=Array.from(name).slice(0,2).join('').toUpperCase();
 accountEl('account-avatar').dataset.color=user.avatar_color||'purple';
 renderAccountPage();
}
function renderAccountPage(){
 if(!accountState)return;
 const u=accountState,name=u.display_name||u.username;
 accountEl('profile-avatar').textContent=Array.from(name).slice(0,2).join('').toUpperCase();
 accountEl('profile-avatar').dataset.color=u.avatar_color;
 accountEl('profile-display-name').textContent=name;
 accountEl('profile-handle').textContent='@'+u.username;
 accountEl('profile-joined').textContent=new Date(u.created_at*1000).toLocaleDateString('th-TH',{year:'numeric',month:'short',day:'numeric'});
 accountEl('profile-username').value=u.username;
 accountEl('display-name').value=name;
 accountEl('profile-bio').value=u.bio||'';
 accountEl('profile-form').elements.avatar_color.value=u.avatar_color||'purple';
 accountEl('settings-form').elements.font_size.value=u.font_size||'large';
 accountEl('default-filter').value=u.default_filter||'all';
 accountEl('font-preview').dataset.size=u.font_size||'large';
}
accountEl('open-profile').onclick=()=>document.querySelector('[data-page="profile"]').click();
accountEl('settings-form').onchange=()=>{accountEl('font-preview').dataset.size=accountEl('settings-form').elements.font_size.value;};
async function saveAccountForm(event,path,done){
 event.preventDefault();const button=event.submitter;button.disabled=true;
 try{const result=await api(path,'PUT',Object.fromEntries(new FormData(event.target)));applyAccount(result.user);renderAccountPage();if(path.endsWith('/settings')){$('filter').value=result.user.default_filter;if(data)render();}notify(done);window.scrollTo({top:0,behavior:'smooth'});}catch(error){notify(error.message,true);window.scrollTo({top:0,behavior:'smooth'});}finally{button.disabled=false;}
}
accountEl('profile-form').onsubmit=event=>saveAccountForm(event,'/api/account/profile','บันทึกโปรไฟล์แล้ว ข้อมูลนี้เป็นของบัญชีคุณเท่านั้น');
accountEl('settings-form').onsubmit=event=>saveAccountForm(event,'/api/account/settings','บันทึกการตั้งค่าแล้ว ใช้ขนาดตัวอักษรและตัวกรองที่เลือกให้เรียบร้อย');
accountEl('password-form').onsubmit=async event=>{
 event.preventDefault();const button=event.submitter,payload=Object.fromEntries(new FormData(event.target));
 if(payload.new_password!==payload.confirm_password){notify('รหัสผ่านใหม่ทั้งสองช่องไม่ตรงกัน',true);return;}
 button.disabled=true;try{await api('/api/account/password','POST',payload);event.target.reset();notify('เปลี่ยนรหัสผ่านแล้ว อุปกรณ์อื่นต้องเข้าสู่ระบบใหม่');window.scrollTo({top:0,behavior:'smooth'});}catch(error){notify(error.message,true);}finally{button.disabled=false;}
};
