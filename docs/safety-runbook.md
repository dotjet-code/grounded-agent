# persona-autopost 安全ランブック

常駐自動投稿エージェントの安全装置と、その訓練記録。
環境戦略v3のP1-1(2026-08-08実施)。

## 安全装置の全体像

| 層 | 装置 | 場所 |
|---|---|---|
| 内容ゲート | SafetyGuard(STOP・静穏時間・日次上限4・クールダウン180分・禁止語・文字数) | `src/persona/outbox.py` |
| 実行ゲート | RunGuard(ランロック=多重実行/暴走防止+ハートビート記録) | `src/persona/safety.py` |
| コスト上限 | LLM呼び出し予算: 1実行あたり最大4回(超過は`BudgetExceeded`で即失敗) | `src/persona/safety.py` |
| キルスイッチ | `scripts/kill_switch.sh`(STOP作成+launchd bootout、検証付き) | 復帰は `scripts/resume_autopost.sh` |
| 死活監視 | `scripts/heartbeat_check.py` を launchd が15分ごとに実行 | `com.grounded-agent.persona-heartbeat` |

監視のアラート条件: ①最終実行から5時間超の沈黙 ②run.lockが30分超残存(ハング/暴走) ③STOPありなのにジョブ残存(半停止)。アラートは `data/logs/safety-alerts.log` +macOS通知。同一アラートは4時間抑制。

## 緊急停止

```bash
bash scripts/kill_switch.sh    # STOP + ジョブ除去 + 検証
bash scripts/resume_autopost.sh  # 復帰
```

X側トークンの失効が必要な場合はdeveloper portalでRegenerate(手動)。

## 訓練記録

| 日付 | 訓練 | 結果 |
|---|---|---|
| 2026-08-08 | 上限遮断: 実ポリシー(max_daily=4)と実投稿記録で「4≥4」遮断を確認。LLM/X到達前にexit 2、heartbeat記録、lock解放 | 合格 |
| 2026-08-08 | キルスイッチ: 発動→STOP遮断(exit 2)→復帰、を実機で確認。**発見と修正**: `launchctl list LABEL`は非GUIシェルで偽陰性(→gui domain照会に修正)。bootout直後のloadはEIOになることがある(→リトライ追加) | 合格(欠陥2件修正) |
| 2026-08-08 | 死活監視: 45分前の偽装run.lockで「ハング検知」、STOP+ジョブ残存で「半停止検知」の両アラート発火。正常状態では無音 | 合格 |

## 既知の挙動(注意)

- `PostingPolicy.from_json`は**ファイルが存在しないと黙ってデフォルト値にフォールバック**する。`--policy`のパスtypoは保守的なデフォルト(上限4)で動くため事故にはならないが、意図した緩和・強化が効かない可能性がある。ポリシー変更時は起動ログで値を確認すること。
- 日次上限はUTC日付基準。JST運用の体感と1日ズレることがある。
- ハートビートは投稿の有無に関わらず毎実行更新される(静穏時間スキップでも更新)。沈黙アラートは「プロセスが起動すらしていない」ことを意味する。

## 次の段階(v3ロードマップとの接続)

- P2-6: 秘密を1Password `op run`へ移行(このランブックの環境変数節も更新する)
- 不在モード: このキルスイッチを全システム共通の縮退コマンドの部品にする(§7人間の運用層)
