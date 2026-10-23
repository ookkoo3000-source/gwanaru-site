# 사이트 이미지 만들기 (Genspark / Nano Banana용 프롬프트)

만든 이미지를 **아래 파일 이름 그대로** 이 `img/` 폴더에 넣으면 사이트에 바로 들어갑니다. 코드는 안 고쳐도 됩니다.
이미지가 없는 칸은 그림(SVG)이 대신 보이므로, 하나씩 채워도 됩니다.

## 모든 프롬프트 앞에 붙이는 공통 스타일

```
Photorealistic 35mm photograph, soft natural window daylight, bright and airy, clean modern Korean home study desk,
white and pale mint-green tones with a few deep teal (#06525c) objects, shallow depth of field,
no readable text, no letters, no logos, no watermark, no people's faces.
```

같은 톤으로 맞추려고 이 문장을 모든 프롬프트 앞에 붙입니다. 글자는 AI가 깨뜨리므로 "글자 없음"을 꼭 유지하세요.

## 1순위 (이 3장이면 사이트가 완성돼 보입니다)

| 파일 이름 | 비율·크기 | 프롬프트 (공통 스타일 뒤에 이어서) |
|---|---|---|
| `hero.jpg` | 3:2 가로, 1500×1000 | A tutor's hand holding a deep teal pen pointing at a math workbook while a Korean middle-school student writes beside it, seen from the side at desk level, both faces out of frame, a laptop slightly open in the background, warm afternoon light. |
| `sheet.jpg` | 4:3 가로, 1200×900 | Top-down view of a single white consultation form on a desk with six blank ruled lines, a hand writing on it with a deep teal ballpoint pen, a phone placed face-down beside it, the writing blurred and illegible. |
| `desk-wide.jpg` | 16:9 가로, 2400×1350 | Wide shot of a bright student study desk by a window: an open laptop showing a blurred video lesson, a notebook and pen, a small plant; the right third of the frame is a calm plain pale wall with soft light (keep it empty, a card will sit there). |

## 2순위 (과목 목록에 마우스를 올리면 보이는 사진 5장, 4:3 가로, 1200×900)

| 파일 이름 | 프롬프트 |
|---|---|
| `subject-math.jpg` | Close-up of a graph-paper notebook with a hand-drawn parabola curve in deep teal ink, a ruler and pencil, equations blurred and illegible. |
| `subject-english.jpg` | Close-up of an English reading passage printed on paper with several lines underlined in teal highlighter, the words out of focus and unreadable, a pencil resting on the page. |
| `subject-korean.jpg` | Close-up of an open Korean literature textbook with a page of prose, one paragraph marked with a teal bracket in the margin, text blurred and unreadable, a sticky note tab on the page edge. |
| `subject-science.jpg` | Close-up of a science lab notebook beside two small glass beakers with pale teal liquid, a hand-drawn diagram of a thermometer and a bar chart in the notebook, labels illegible. |
| `subject-social.jpg` | Close-up of a notebook with a hand-drawn horizontal timeline with five dots in teal ink, a small folded map and a highlighter beside it, all labels blurred. |

## 3순위

| 파일 이름 | 비율·크기 | 프롬프트 |
|---|---|---|
| `stamp.jpg` | 3:4 세로, 300×400 | A single deep teal ballpoint pen standing upright in a small white ceramic cup on a white desk, centered, plenty of empty space around it. |

## 넣는 방법

1. 만든 이미지를 위 파일 이름으로 저장합니다 (확장자 `.jpg`, 대소문자 그대로).
2. `img/` 폴더에 넣고 깃허브에 올리면(push) 끝입니다.
3. 비율이 조금 달라도 칸에 맞게 잘려서 보이지만, 세로·가로 방향은 맞춰 주세요.
4. 용량은 한 장에 300KB 안쪽이 좋습니다. 크면 squoosh.app 같은 곳에서 줄이세요.
