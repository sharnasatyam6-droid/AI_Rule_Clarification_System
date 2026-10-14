import {createHmac,timingSafeEqual} from "node:crypto";
import {cookies} from "next/headers";
const COOKIE="rulebook_admin";
function secret(){return process.env.ADMIN_SESSION_SECRET||process.env.NEON_AUTH_COOKIE_SECRET||""}
function signature(value:string){return createHmac("sha256",secret()).update(value).digest("base64url")}
export function adminConfigured(){return Boolean(process.env.ADMIN_USERNAME&&process.env.ADMIN_PASSWORD&&secret())}
export async function isAdmin(){if(!adminConfigured())return false;const jar=await cookies(),raw=jar.get(COOKIE)?.value;if(!raw)return false;const [payload,sig]=raw.split(".");if(!payload||!sig)return false;const expected=signature(payload);const a=Buffer.from(sig),b=Buffer.from(expected);if(a.length!==b.length||!timingSafeEqual(a,b))return false;try{const data=JSON.parse(Buffer.from(payload,"base64url").toString("utf8"));return data.u===process.env.ADMIN_USERNAME&&Number(data.e)>Date.now()}catch{return false}}
export async function setAdminCookie(){const jar=await cookies(),payload=Buffer.from(JSON.stringify({u:process.env.ADMIN_USERNAME,e:Date.now()+8*60*60*1000})).toString("base64url");jar.set(COOKIE,payload+"."+signature(payload),{httpOnly:true,secure:process.env.NODE_ENV==="production",sameSite:"strict",path:"/",maxAge:8*60*60})}
export async function clearAdminCookie(){const jar=await cookies();jar.delete(COOKIE)}
