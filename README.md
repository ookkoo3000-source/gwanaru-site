# 과외나루 — 사이트 사용 설명

초중고 방문·화상 1:1 과외 상담 사이트. 정적 HTML이라 서버가 필요 없고, 깃허브에 올리면 GitHub Pages가 그대로 서빙합니다.

## 폴더 구성

| 위치 | 하는 일 |
|---|---|
| `data/content.py` | **사이트의 모든 문구**(전화번호, 수업료, FAQ, 과목 설명). 고칠 때는 여기만 고치면 됩니다 |
| `templates/index.html` | 메인 페이지 틀 |
| `posts/*.md` | **블로그 글**. 파일 하나 = 글 하나 = 개별 페이지 (`posts/README.md` 참고) |
| `build.py` | 위 세 가지로 모든 페이지, `sitemap.xml`, `rss.xml`, `robots.txt`를 만듭니다 |
| `css/`, `js/`, `img/` | 디자인과 스크립트, OG 이미지 |
| `.github/workflows/build.yml` | 깃허브에 push할 때마다 자동으로 빌드하고 배포 |

생성된 폴더(`elementary-math/`, `blog/` …)는 `build.py`가 다시 만들기 때문에 직접 고치지 마세요.

## 처음 올리기

1. 깃허브에서 새 저장소를 만들고 이 폴더를 통째로 올립니다 (브랜치 이름 `main`).
2. 저장소 **Settings → Pages → Build and deployment → Source**를 **GitHub Actions**로 바꿉니다.
3. **Settings → Pages → Custom domain**에 도메인을 넣고, 도메인 업체에서 CNAME을 `아이디.github.io`로 잡습니다.
4. `data/content.py`의 `SITE_URL`을 실제 도메인(`https://도메인`, 끝에 `/` 없이)으로 바꾸고 push합니다.
   `SITE_URL`이 맞아야 사이트맵·RSS·canonical 주소가 맞습니다.

로컬에서 미리 보려면: `pip install -r requirements.txt` 후 `python3 build.py`, 그리고 `index.html`을 브라우저로 열면 됩니다.

## 글 올리기 (하루 5~10개)

`posts/` 폴더에 `.md` 파일을 넣고 push하면 끝입니다. 약 1분 뒤 `/blog/파일이름/` 주소로 개별 페이지가 생기고, 사이트맵과 RSS에 자동으로 들어갑니다. 형식은 `posts/README.md`에 있습니다.

## 네이버 검색 등록 (사이트 올린 뒤 꼭)

1. [네이버 서치어드바이저](https://searchadvisor.naver.com) → 웹마스터 도구 → 사이트 등록 (도메인 입력).
2. **소유 확인**에서 "HTML 태그" 방식을 고르면 `<meta name="naver-site-verification" content="…">` 코드가 나옵니다.
   그 `content` 값을 `data/content.py`의 `NAVER_VERIFY`에 넣고 push → 배포된 뒤 "소유확인" 버튼.
3. **요청 → 사이트맵 제출**: `https://도메인/sitemap.xml`
4. **요청 → RSS 제출**: `https://도메인/rss.xml`
5. **요청 → 웹 페이지 수집**: 메인 주소와 중요한 페이지 몇 개를 직접 넣어 두면 첫 수집이 빨라집니다.
6. 등록 후 노출까지 보통 2주 안팎 걸립니다. 이후에는 새 글이 RSS를 타고 자동으로 수집됩니다.

구글도 같이 하려면 [Google Search Console](https://search.google.com/search-console)에 같은 사이트맵을 제출하면 됩니다.

## 네이버 노출을 위해 이미 되어 있는 것

- 페이지마다 고유한 `<title>`, `description`, `canonical`, Open Graph
- 주소가 `?id=123`이 아니라 `/middle-math/`처럼 의미 있는 경로
- 핵심 내용이 전부 텍스트(이미지에 글자 넣지 않음), 모든 그림에 alt
- `robots.txt`에 네이버 봇(Yeti) 허용, `sitemap.xml`·`rss.xml` 자동 생성
- 구조화 데이터(JSON-LD): 메인은 LocalBusiness + FAQ, 안내 페이지는 FAQ, 블로그 글은 Article
- 학년×과목(15) + 학년 허브(3) + 화상/방문/비용(3) 안내 페이지가 서로 링크
- 모바일 우선 레이아웃, 외부 스크립트 없음

노출 순위는 네이버가 정하는 것이라 어떤 사이트도 "무조건 상위"를 약속할 수는 없습니다. 위 구조 위에서 **매일 글을 올리고, 글마다 제목에 학년·과목·상황 키워드를 넣는 것**이 가장 큰 변수입니다.

## 꼭 확인해서 고칠 것

- **수업료 범위**: `data/content.py`의 `price`는 참고한 회사 안내표(월 기준으로 추정)를 옮긴 것입니다. 회사 기준과 맞는지 확인하세요.
- **상담 가능 시간**(평일 09–21, 주말 10–18)은 임의로 넣은 값입니다. `templates/index.html`의 "상담 신청" 카드와 JSON-LD `openingHours`를 고치세요.
- **사이트 이름 "과외나루"**: 바꾸려면 `data/content.py`의 `SITE_NAME`과 `templates/index.html`의 제목·본문을 같이 고치세요.
- **사업자 정보**: 회사 소속으로 영업한다면 푸터에 상호·사업자번호를 넣는 것이 좋습니다. 회사와 상의하세요.
- **사진**: 지금은 그림(SVG)이 자리를 채우고 있습니다. `img/PROMPTS.md`의 프롬프트로 이미지를 만들어 같은 파일 이름으로 `img/`에 넣으면 자동으로 사진이 들어갑니다.
