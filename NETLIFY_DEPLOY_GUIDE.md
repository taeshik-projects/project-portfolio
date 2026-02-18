# 📦 Netlify 배포 가이드

## 📋 준비된 파일 목록

✅ **필수 파일:**
- `portfolio-dashboard.html` - 메인 HTML 파일 (기존)
- `robots.txt` - 검색엔진 크롤러 차단
- `netlify.toml` - Netlify 설정 (보안 헤더, SPA 라우팅)
- `_redirects` - 리다이렉트 규칙

## 🔒 보안 설정 요약

생성된 파일들에 포함된 보안 설정:

### robots.txt
- 모든 검색엔진 크롤러 차단 (`User-agent: * / Disallow: /`)
- 사이트가 Google, Bing 등 검색 결과에 나타나지 않음

### netlify.toml 보안 헤더
- **XSS 보호**: X-Frame-Options, X-XSS-Protection
- **HTTPS 강제**: Strict-Transport-Security (1년)
- **콘텐츠 보안**: Content-Security-Policy (외부 스크립트 제한)
- **캐싱 최적화**: HTML은 no-cache, CSS/JS는 1년 캐싱

### _redirects
- 루트 경로(`/`)를 자동으로 portfolio-dashboard.html로 연결
- 404 에러 방지 (모든 경로를 메인 페이지로)

---

## 🚀 배포 방법 1: 드래그 앤 드롭 (가장 간단)

### 1단계: Netlify 로그인
1. [https://app.netlify.com/](https://app.netlify.com/) 접속
2. GitHub/GitLab/이메일로 회원가입 또는 로그인

### 2단계: 사이트 배포
1. **"Add new site"** 버튼 클릭
2. **"Deploy manually"** 선택
3. 다음 4개 파일을 한 번에 드래그 앤 드롭:
   ```
   portfolio-dashboard.html
   robots.txt
   netlify.toml
   _redirects
   ```
4. 업로드 완료 대기 (10~30초)

### 3단계: 사이트 접속
- 자동으로 생성된 URL 확인 (예: `https://random-name-123456.netlify.app`)
- 즉시 접속 가능!

### 4단계 (선택사항): 도메인 변경
1. **Site settings** → **Domain management**
2. **Change site name** 클릭
3. 원하는 이름 입력 (예: `tsk-portfolio` → `https://tsk-portfolio.netlify.app`)

---

## 💻 배포 방법 2: Netlify CLI (고급 사용자)

### 1단계: CLI 설치
```bash
# npm 사용
npm install -g netlify-cli

# 또는 Homebrew (Mac)
brew install netlify-cli
```

### 2단계: 로그인
```bash
netlify login
```
- 브라우저가 열리면 로그인 후 인증

### 3단계: 배포 디렉토리로 이동
```bash
cd /Users/tsk/.openclaw/workspace
```

### 4단계: 초기 배포
```bash
netlify deploy
```

실행 후 질문 답변:
- **"Create & configure a new site"** 선택
- **Team**: 본인 계정 선택
- **Site name**: 원하는 이름 입력 (비워두면 랜덤)
- **Publish directory**: `.` (현재 디렉토리) 입력

### 5단계: 프로덕션 배포
테스트 URL 확인 후 문제없으면:
```bash
netlify deploy --prod
```

### 6단계: 자동화 스크립트 (선택사항)
이후 업데이트 시 빠른 배포를 위해:

```bash
# deploy.sh 파일 생성
cat > deploy.sh << 'EOF'
#!/bin/bash
echo "🚀 Netlify 배포 시작..."
netlify deploy --prod --dir=.
echo "✅ 배포 완료!"
netlify open:site
EOF

chmod +x deploy.sh

# 실행
./deploy.sh
```

---

## 🔧 배포 후 확인 사항

### 1. 사이트 접속 테스트
- 메인 URL 접속: `https://your-site.netlify.app`
- 자동으로 portfolio-dashboard.html이 표시되는지 확인

### 2. 보안 헤더 확인
브라우저 개발자 도구 (F12) → Network 탭:
```
Status: 200 OK
X-Frame-Options: DENY
Strict-Transport-Security: max-age=31536000
Content-Security-Policy: (설정된 정책 확인)
```

### 3. robots.txt 확인
- `https://your-site.netlify.app/robots.txt` 접속
- "Disallow: /" 표시되는지 확인

### 4. 리다이렉트 테스트
- `https://your-site.netlify.app/` → portfolio-dashboard.html로 이동
- `https://your-site.netlify.app/random` → 404 없이 메인 페이지 표시

---

## 📱 추가 기능

### 사용자 정의 도메인 연결
1. Netlify 대시보드 → **Domain settings**
2. **Add custom domain** 클릭
3. 본인 소유 도메인 입력 (예: `portfolio.yourdomain.com`)
4. DNS 설정 안내에 따라 CNAME 레코드 추가

### HTTPS 인증서
- Netlify가 자동으로 Let's Encrypt SSL 인증서 발급 (무료)
- 배포 후 5~10분 내 자동 활성화

### 배포 알림 설정
1. **Site settings** → **Build & deploy** → **Deploy notifications**
2. 이메일/Slack 알림 추가 가능

---

## 🆘 문제 해결

### Chart.js가 로드되지 않을 때
- `netlify.toml`의 Content-Security-Policy에 이미 `https://cdn.jsdelivr.net` 허용됨
- 브라우저 콘솔(F12)에서 에러 확인

### 페이지가 표시되지 않을 때
1. 배포된 파일 목록 확인: Netlify 대시보드 → **Deploys** → 최신 배포 클릭
2. 4개 파일 모두 업로드되었는지 확인

### CLI 권한 오류
```bash
# 로그아웃 후 재로그인
netlify logout
netlify login
```

---

## 📊 배포 완료 체크리스트

- [ ] 4개 파일 모두 업로드됨
- [ ] 사이트 URL 접속 가능
- [ ] 차트가 정상적으로 표시됨
- [ ] robots.txt 접속 시 "Disallow: /" 표시
- [ ] 브라우저 개발자 도구에서 보안 헤더 확인
- [ ] (선택) 사이트 이름 변경 완료
- [ ] (선택) 사용자 정의 도메인 연결

---

## 🎉 완료!

이제 포트폴리오 대시보드가 전 세계 어디서나 빠르게 접속 가능한 Netlify CDN에 배포되었습니다.

**업데이트가 필요할 때:**
- 드래그 앤 드롭: 같은 방법으로 파일 재업로드 (새 버전 자동 배포)
- CLI: `netlify deploy --prod` 실행

**URL 공유 시 주의:**
- 검색엔진에는 노출되지 않지만, URL을 아는 사람은 접속 가능
- 완전한 비공개 원한다면 Netlify의 Password Protection 기능 사용 (유료 플랜)
