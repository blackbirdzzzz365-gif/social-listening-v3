# Social Listening v3 Codex Product Loop

Tai lieu nay chot cach ban va Codex phoi hop de van hanh vong lap phat trien san pham dua tren production truth cho `social-listening-v3`.

Muc tieu cua workflow nay:

1. bat dau bang production evidence that
2. dung lai o checkpoint verdict de ban chot huong
3. de Codex tu branch/docs/checkpoints/implementation trong mot workspace an toan
4. dung lai o candidate summary de ban quyet merge/deploy hay iterate them
5. sau deploy, quay lai production audit

Skill entrypoint cho repo nay:

- `social-listening-v3-product-loop`
- `social-listening-v3-production-audit`
- `social-listening-v3-phase-executor`

## 1. State machine chuan

### B1 - Production audit

Dung `social-listening-v3-production-audit` khi ban muon:

- chay live 1-2 case that tren production
- doc lai artifact cu trong `reports/production/`
- doi chieu production voi muc tieu cua phase hien tai
- ra `checkpoint verdict`

Codex phai:

1. doc `.phase.json`
2. doc `docs/phases/<current-phase>/README.md` va, neu can, `technical-solution.md`
3. chon 1-2 case tu case pack mac dinh trong `.phase.json` hoac dung subset ban chi ro
4. neu ban cho phep chay live, goi `scripts/run_production_case_pack.py`
5. doi chieu `final_report.md`, `latest_analysis.json`, `bootstrap.json`, `case.json` voi goal/expectation/success signals cua phase
6. viet `checkpoint verdict`
7. dung lai de ban chot huong

Artifact path mac dinh cho checkpoint verdict:

- `docs/phases/<current-phase>/analysis/checkpoint-verdict-<YYYYMMDD-HHMM>.md`

Route duoc phep sau checkpoint verdict:

- `contained-fix`
- `new-phase`
- `rerun-observation`

### B2 - Direction lock va execution

Dung `social-listening-v3-phase-executor` sau khi ban da chot huong ro rang.

Codex phai:

1. doc `checkpoint verdict` moi nhat
2. lay latest `main`
3. neu working tree hien tai dirty hoac dang co viec dang lam, tao worktree moi tu `main`
4. tao branch `codex/<scope>`
5. dong goi docs phu hop voi route:
   - `contained-fix`: tao patch package toi thieu
   - `new-phase`: tao full phase package
6. phan tich technical delta
7. break checkpoint
8. implement lan luot theo checkpoint
9. validate
10. viet `candidate summary`
11. dung lai

Worktree convention:

- root: `../social-listening-v3-worktrees`
- duong dan de xuat: `../social-listening-v3-worktrees/<branch-name>`

Artifact path convention:

- `contained-fix`: `docs/phases/<current-phase>/patches/<YYYYMMDD>-<slug>/`
- `new-phase`: `docs/phases/<next-phase>/`
- candidate summary: dat trong patch dir hoac phase dir, ten `candidate-summary.md`

### B3 - Merge/deploy gate

Tai gate nay, ban chi chon mot huong:

- `merge-and-deploy`
- `brainstorm-and-iterate`

Neu ban chua muon merge, Codex phai dung lai va tiep tuc brainstorm/iterate tren branch hien tai hoac branch moi theo chi dao cua ban.

### B4 - Revalidation

Sau deploy production that, quay lai B1:

- chay 1-2 case live tu case pack
- hoac chay lai dung subset da tung gay loi
- doi chieu voi `candidate summary` va muc tieu phase vua ship

## 2. File contract cho workflow nay

Source of truth:

- `.phase.json`
- `docs/production/case-packs/phase-10-core.json`
- `docs/templates/checkpoint-verdict-template.md`
- `docs/templates/phase-manifest-template.md`
- `docs/templates/candidate-summary-template.md`
- `docs/phases/<phase>/README.md`

Runtime artifact:

- `reports/production/<run_id>/case.json`
- `reports/production/<run_id>/bootstrap.json`
- `reports/production/<run_id>/latest_analysis.json`
- `reports/production/<run_id>/final_report.md`
- `reports/production/case-packs/<pack-id>-latest.json`

Helper script:

- `scripts/run_production_case_pack.py`

Lenh de chay tay neu can:

```bash
python scripts/run_production_case_pack.py docs/production/case-packs/phase-10-core.json --case phase10-fe-credit-answer-closeout --limit 1
```

Dry run de kiem tra mapping ma khong trigger production:

```bash
python scripts/run_production_case_pack.py docs/production/case-packs/phase-10-core.json --case phase10-ngu-hoa-image-bearing --dry-run
```

## 3. Cach noi chuyen voi Codex de hieu qua nhat

### Nguyen tac 1 - Moi prompt chi co 1 gate

Khong tron audit, execution, merge, va revalidation vao mot prompt dai.

Nen tach thanh:

1. audit
2. chot huong
3. merge/deploy gate
4. re-audit

### Nguyen tac 2 - Luon noi ro live hay artifact-only

Vi du:

- `Chay live 2 case dau trong case pack mac dinh.`
- `Khong chay production that. Chi doc artifact cu va cho toi checkpoint verdict.`

### Nguyen tac 3 - Chot huong bang keyword on dinh

Dung cau mo dau nhu sau:

- `Chot huong: contained-fix.`
- `Chot huong: new-phase.`
- `Chot huong: rerun-observation.`

Neu ban khong bat dau bang cau nay, Codex de roi vao trang thai vua brainstorm vua code.

### Nguyen tac 4 - Noi ro workspace safety

Repo nay thuong dirty.
Neu ban muon Codex khong dong vao workspace dang mo, noi ro:

- `Dung worktree moi tu main.`

Neu ban muon Codex tiep tuc ngay trong current working tree, cung can noi ro:

- `Lam ngay trong workspace hien tai, khong tao worktree moi.`

### Nguyen tac 5 - Gate cuoi cung phai ro rang

Neu ban chua muon merge/deploy, noi ro:

- `Dung truoc gate merge.`
- `Brainstorm them 2 huong.`

Neu ban da muon merge/deploy, noi ro:

- `Khong brainstorm them. Chuan bi merge/deploy gate cho toi review.`

## 4. Prompt patterns nen dung

### A. Chay production audit

```text
Dung social-listening-v3-production-audit cho phase hien tai.
Chay live 2 case dau trong case pack mac dinh.
So sanh voi muc tieu phase hien tai va dung lai o checkpoint verdict de toi chot huong.
```

### B. Chot huong va vao execution

```text
Chot huong: new-phase.
Dung social-listening-v3-phase-executor.
Lay latest main, dung worktree moi neu current tree dirty, tao branch codex/phase-10-answer-quality,
dong goi docs day du, break checkpoint, implement, validate, va bao cao candidate summary.
```

### C. Chi sua contained fix

```text
Chot huong: contained-fix.
Dung social-listening-v3-phase-executor.
Khong mo phase moi. Tao patch package toi thieu, break checkpoint can thiet, implement, validate, va dung o candidate summary.
```

### D. Merge/deploy gate

```text
Candidate summary da on.
Khong brainstorm them.
Chuan bi merge/deploy gate cho toi review nhanh, nhung dung lai truoc khi merge neu toi chua chot.
```

### E. Revalidation sau deploy

```text
Sau deploy, dung social-listening-v3-production-audit.
Chay lai 2 case da duoc sua trong candidate summary va so sanh voi checkpoint verdict truoc do.
```

## 5. Bon vi du end-to-end cu the

### Vi du 1 - Ngu Hoa audit -> new phase -> candidate summary

Muc tieu:

- kiem tra Phase 9 da bien accepted evidence thanh answer duoc hay chua

Prompt 1:

```text
Dung social-listening-v3-production-audit cho phase hien tai.
Chay live case `ngu-hoa-market-sentiment` va `tpbank-evo-general-feedback`.
So sanh voi muc tieu Phase 9, viet checkpoint verdict, roi dung lai.
```

Codex nen tra lai:

- run ids vua chay
- verdict path
- expectation vs actual
- route de xuat

Prompt 2:

```text
Chot huong: new-phase.
Phase 10 phai giai quyet answer quality sau closeout va source memory giua cac run.
Dung social-listening-v3-phase-executor.
Lay latest main, dung worktree moi neu can, tao branch codex/phase-10-answer-quality,
dong goi phase docs day du, break checkpoint, implement, validate, va dung o candidate summary.
```

Codex nen tra lai:

- worktree path
- branch name
- docs phase moi
- checkpoint plan
- candidate summary path

Prompt 3:

```text
Dung truoc gate merge.
Brainstorm them 2 huong de cai thien source memory truoc khi toi quyet deploy.
```

### Vi du 2 - TPBank EVO general feedback -> contained fix -> merge gate

Muc tieu:

- check browser safety va answer closeout tren case smoke that

Prompt 1:

```text
Dung social-listening-v3-production-audit.
Chi chay case `tpbank-evo-general-feedback`.
Neu thay loi van nam trong scope phase hien tai thi de xuat contained-fix.
```

Prompt 2:

```text
Chot huong: contained-fix.
Chi sua browser lease va closeout retry.
Dung social-listening-v3-phase-executor.
Dung worktree moi tu main, tao patch package toi thieu, implement, validate, va dung o candidate summary.
```

Prompt 3:

```text
Candidate summary da on.
Khong brainstorm them.
Chuan bi merge/deploy gate cho toi review nhanh.
```

### Vi du 3 - Fee complaint -> route quality fix -> revalidation

Muc tieu:

- xac dinh complaint posture co duoc uu tien som hon chua

Prompt 1:

```text
Dung social-listening-v3-production-audit.
Chay live case `tpbank-evo-fee-complaint`.
Tap trung danh gia route ordering, reject reasons, va reformulation quality.
```

Neu Codex bao `route decision = contained-fix`, ban tra loi:

```text
Chot huong: contained-fix.
Fix yield-aware routing va reason-aware reformulation trong scope phase hien tai.
Dung social-listening-v3-phase-executor va dung o candidate summary.
```

Sau deploy, prompt tiep:

```text
Sau deploy, dung social-listening-v3-production-audit.
Chay lai case `tpbank-evo-fee-complaint` de so sanh delta voi candidate summary va checkpoint verdict truoc do.
```

### Vi du 4 - Vision validation -> phase closeout

Muc tieu:

- dong Phase 9 bang mot image-bearing case that

Prompt 1:

```text
Dung social-listening-v3-production-audit.
Chay case `ngu-hoa-image-bearing-validation`.
Neu can, doi chieu them voi Phase 9 CP5 va muc tieu P2 vision validation.
```

Prompt 2:

```text
Chot huong: contained-fix.
Hoan tat phan vision validation con thieu.
Dung social-listening-v3-phase-executor.
Khong mo phase moi. Tao patch package, implement, validate, tao candidate summary, roi dung.
```

Prompt 3:

```text
Khong brainstorm them.
Toi muon merge/deploy sau khi toi review nhanh candidate summary.
Hay chuan bi merge/deploy gate cho toi.
```

Prompt 4 sau deploy:

```text
Sau deploy, dung social-listening-v3-production-audit.
Chay lai case `ngu-hoa-image-bearing-validation` va `tpbank-evo-general-feedback`
de check Phase 9 da on tren ca vision case va smoke case hay chua.
```

## 6. Anti-pattern nen tranh

Khong nen prompt nhu sau:

- `Check het giup toi roi tu quyet merge neu on.`
- `Vua chay production vua code vua deploy luon.`
- `Lam tiep theo cach ban thay hop ly.`

Ly do:

- mat human gate sau checkpoint verdict
- mat human gate truoc merge/deploy
- Codex phai doan scope thay vi theo production truth va chi dao cua ban
