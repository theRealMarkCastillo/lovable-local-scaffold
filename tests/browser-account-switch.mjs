// Real local Auth/RLS plus delayed responses: private data must not cross accounts.
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {fileURLToPath,pathToFileURL} from 'node:url';
import path from 'node:path';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const env=Object.fromEntries((await readFile(path.join(root,'.env'),'utf8')).split('\n')
  .filter(line=>line.includes('=')&&!line.startsWith('#')).map(line=>[line.slice(0,line.indexOf('=')),line.slice(line.indexOf('=')+1)]));
const base=env.PUBLIC_URL.replace(/\/$/,'');
const host=new URL(base).hostname;
assert(host==='localhost'||host==='127.0.0.1'||host.endsWith('.orb.local'),'Browser regression is local-only');
const modulePath=process.env.SCAFFOLD_PLAYWRIGHT_PATH||path.join(root,'.runtime/browser-tools/node_modules/playwright/index.mjs');
const {chromium}=await import(pathToFileURL(modulePath).href);
const channel=process.env.SCAFFOLD_BROWSER_CHANNEL||'chrome';
const browser=await chromium.launch({headless:true,...(channel==='chromium'?{}:{channel})});
const context=await browser.newContext();
const page=await context.newPage();
const api=base+'/supabase';const headers={apikey:env.ANON_KEY};
const mail='http://localhost:'+env.MAIL_PORT;
const stamp=Date.now()+'-'+Math.random().toString(16).slice(2);
const errors=[];page.on('pageerror',error=>errors.push(error.message));
function bounded(promise,label){let timer;return Promise.race([promise,new Promise((_,reject)=>{timer=setTimeout(()=>reject(new Error('Timed out waiting for '+label)),30000);})]).finally(()=>clearTimeout(timer));}
function gate(){let resolve;const promise=new Promise(done=>resolve=done);return {promise,resolve};}
const releaseA=gate(),releaseB=gate(),startedA=gate(),startedB=gate();
const pending=[];
async function account(label){
 const user={email:`review-${label}-${stamp}@example.test`,password:'Local-review-password-'+stamp+'aA1!'};
 assert((await context.request.post(api+'/auth/v1/signup',{headers,data:user})).ok());
 let message;
 for(let i=0;i<30;i++){
  const list=await (await context.request.get(mail+'/api/v1/messages')).json();
  const found=list.messages.find(value=>value.To.some(to=>to.Address===user.email));
  if(found){message=await (await context.request.get(mail+'/api/v1/message/'+found.ID)).json();break;}
  await new Promise(done=>setTimeout(done,100));
 }
 assert(message,'Captured confirmation email missing');
 const link=message.HTML.match(/href="([^"]*\/auth\/v1\/verify[^\"]*)"/)[1].replaceAll('&amp;','&');
 assert.equal(new URL(link).origin,new URL(base).origin);
 assert((await context.request.get(link)).ok());
 const response=await context.request.post(api+'/auth/v1/token?grant_type=password',{headers,data:user});
 assert(response.ok());const session=await response.json();
 return {...user,id:session.user.id,token:session.access_token};
}
async function note(user,title){
 assert((await context.request.post(api+'/rest/v1/notes',{headers:{...headers,Authorization:'Bearer '+user.token},data:{title,body:'Synthetic delayed-response regression'}})).ok());
}
try{
 const a=await account('a'),b=await account('b');
 const markerA='Private A '+stamp,markerB='Private B '+stamp,fileA='private-a-'+stamp+'.txt';
 await note(a,markerA);await note(b,markerB);
 assert((await context.request.post(api+'/storage/v1/object/uploads/'+a.id+'/'+fileA,{headers:{...headers,Authorization:'Bearer '+a.token,'Content-Type':'text/plain'},data:Buffer.from('Synthetic private A file')})).ok());
 let aCount=0,bCount=0;
 const heldA=new Set();
 async function intercept(route){
  const token=route.request().headers().authorization?.split(' ')[1];
  const subject=token?JSON.parse(Buffer.from(token.split('.')[1],'base64url').toString()).sub:null;
  const kind=route.request().url().includes('/rest/v1/')?'notes':'files';
  if(subject===a.id&&!heldA.has(kind)){
   heldA.add(kind);const response=await route.fetch();
   if(++aCount===2)startedA.resolve();
   await releaseA.promise;return route.fulfill({response});
  }
  if(subject===b.id){
   if(++bCount===2)startedB.resolve();
   await releaseB.promise;
  }
  return route.continue();
 }
 for(const pattern of ['**/rest/v1/notes?*','**/storage/v1/object/list/uploads'])
  await page.route(pattern,route=>{const work=intercept(route);pending.push(work);return work;});
 async function login(user){
  await page.getByLabel('Email',{exact:true}).fill(user.email);
  await page.getByLabel('Password',{exact:true}).fill(user.password);
  await page.getByRole('button',{name:'Sign in',exact:true}).click();
  await page.getByText('Signed in as '+user.email,{exact:true}).waitFor();
 }
 await page.goto(base);await login(a);await bounded(startedA.promise,'A reads');
 await page.getByRole('button',{name:'Sign out',exact:true}).click();
 await page.getByRole('heading',{name:'Sign in to your workspace'}).waitFor();
 releaseA.resolve();await Promise.allSettled([...pending]);
 await page.evaluate(()=>new Promise(done=>requestAnimationFrame(()=>requestAnimationFrame(done))));
 await login(b);await bounded(startedB.promise,'B reads');
 assert.equal(await page.getByText(markerA,{exact:true}).count(),0,'User A note rendered under B');
 assert.equal(await page.getByText(fileA,{exact:true}).count(),0,'User A file metadata rendered under B');
 releaseB.resolve();await page.getByText(markerB,{exact:true}).waitFor();
 assert.equal(await page.getByText(markerA,{exact:true}).count(),0);
 assert.equal(await page.getByText(fileA,{exact:true}).count(),0);
 assert.deepEqual(errors,[]);
 console.log('PASS: delayed notes/files from A never render under B; B data loads after release');
 console.log('Synthetic local users, notes and files retained; no cloud backend contacted.');
}finally{
 releaseA.resolve();releaseB.resolve();await Promise.allSettled(pending);await browser.close();
}
