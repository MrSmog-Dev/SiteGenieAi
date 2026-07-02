# Auth Testing Playbook (SiteGenie)

Auth: opaque session tokens in `user_sessions`, delivered via httpOnly `session_token` cookie (also accepted as `Authorization: Bearer <token>`). Two entry paths: email/password (bcrypt) and Emergent-managed Google OAuth.

## Admin
- Email: admin@sitegenie.com
- Password: admin123

## API tests
```
curl -c cookies.txt -X POST http://localhost:8001/api/auth/login -H "Content-Type: application/json" -d '{"email":"admin@sitegenie.com","password":"admin123"}'
curl -b cookies.txt http://localhost:8001/api/auth/me
```
Login returns user object + sets session_token cookie. /me returns same user.

## Google flow (for browser test)
Create a session directly in Mongo:
```
mongosh --eval "
use('test_database');
var uid='user_test'+Date.now();
db.users.insertOne({user_id:uid,email:'g'+Date.now()+'@ex.com',name:'G Test',picture:'',role:'user',credits:5,plan:null,created_at:new Date()});
db.user_sessions.insertOne({user_id:uid,session_token:'test_session_x',expires_at:new Date(Date.now()+7*24*3600*1000),created_at:new Date()});
"
```
Then set cookie `session_token=test_session_x` (secure, sameSite None) and load /dashboard.

## Protected endpoints
- GET  /api/templates
- POST /api/templates/generate  (costs 1 credit)
- POST /api/checkout/session    { kind, plan_id, origin_url }
- GET  /api/checkout/status/{session_id}
