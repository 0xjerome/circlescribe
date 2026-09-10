# CircleScribe — Final Submission Checklist

## Repository
- [ ] `main` is clean and pushed
- [ ] latest GitHub Actions run is green
- [ ] README matches the final implementation
- [ ] MIT license and architecture diagram are present
- [ ] no keys, tokens, `.env`, recordings, or SQLite DB are committed
- [ ] `./scripts/submission_check.sh` passes

## Product proof
- [ ] correction demo produces Amina 50k, John 20k, Mary 40k
- [ ] John's original 30k is superseded
- [ ] Sarah 100k loan request stays out of the ledger
- [ ] ambiguity demo blocks uncertain 50k
- [ ] confirm and discard paths work
- [ ] artifacts remain blocked before review
- [ ] Recent meetings reopens a resolved run
- [ ] minutes, receipts, audit/evidence exports work

## AWS — do not overclaim
- [ ] account verification resolved
- [ ] valid Bedrock API key generated
- [ ] `python backend/scripts/aws_smoke.py` passes
- [ ] `/api/v1/extract` works through real Strands + Bedrock
- [ ] claim Transcribe/DynamoDB/S3/AgentCore/CloudWatch only if actually connected
- [ ] update/remove temporary AWS-status wording before submission

## Video
- [ ] public YouTube/Vimeo URL
- [ ] under 5:00
- [ ] working product appears early
- [ ] correction + ambiguity scenarios shown
- [ ] architecture and CI shown briefly
- [ ] no secrets/account numbers/private email visible
- [ ] AWS claims match what visibly works

## Devpost
- [ ] Project: CircleScribe
- [ ] Track: Good Neighbor Agents
- [ ] Submitter: Individual
- [ ] Country: Uganda
- [ ] all narrative sections pasted
- [ ] public GitHub linked
- [ ] video linked
- [ ] live demo linked only if reliable

## Final check
- [ ] open repo/video/live demo in incognito
- [ ] remove stale planned-vs-implemented claims
- [ ] submit with time to spare
