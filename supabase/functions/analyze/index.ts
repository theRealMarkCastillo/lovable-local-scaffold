// Functions use the caller's user token, never service-role access for user data.
const publicOrigin = new URL(Deno.env.get('SUPABASE_PUBLIC_URL')!).origin;
const cors = {'Access-Control-Allow-Origin': publicOrigin, 'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type', 'Access-Control-Allow-Methods': 'POST, OPTIONS', 'Vary': 'Origin'};
Deno.serve(async req => {
  if (req.method === 'OPTIONS') return new Response(null, {status:204,headers:cors});
  const respond = (body:unknown,status=200) => Response.json(body,{status,headers:cors});
  if (req.method !== 'POST') return respond({error:'POST required'},405);
  const authorization=req.headers.get('authorization') || '';
  if (!authorization.startsWith('Bearer ')) return respond({error:'Sign in first'},401);
  const identity=await fetch(Deno.env.get('SUPABASE_URL')+'/auth/v1/user',{
    headers:{apikey:Deno.env.get('SUPABASE_ANON_KEY')!, authorization}
  });
  if (!identity.ok) return respond({error:'Invalid user session'},401);
  if (Number(req.headers.get('content-length') || 0)>32000) return respond({error:'Body too large'},413);
  let payload;
  try { const raw=await req.text(); if(raw.length>24000)return respond({error:'Body too large'},413); payload=JSON.parse(raw); }
  catch {return respond({error:'Invalid JSON'},400);}
  if(typeof payload.text!=='string'||payload.text.length>4000)return respond({error:'Provide text up to 4000 characters'},400);
  return respond({words:payload.text.trim().split(/\s+/u).filter(Boolean).length,characters:payload.text.length});
});
