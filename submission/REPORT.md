# Báo cáo cá nhân — K4-L3A Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Nguyễn Thu Trang
- **MSSV:** 2A202602435
- **Lớp:** K4-L3A
- **Repository URL:** `https://github.com/trangnguyen2k5-sketch/K4-L3-DAY13-NguyenThuTrang-2A202602435-Monitoring-LLMOps`
- **Commit SHA cuối:** *b219027599862952895455daf4ada12fc104608c*
- **Challenge ID:** `day13-k4-l3a-monitoring-llmops-v1`
- **Tên project Langfuse cá nhân:** `day13-k4-l3a-2A202602435`

## 2. Evidence index

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | [evidence/01-pytest.png](evidence/01-pytest.png) |
| Log validator | [evidence/02-log-validator.png](evidence/02-log-validator.png) |
| Dashboard validator | [evidence/03-dashboard-validator.png](evidence/03-dashboard-validator.png) |
| Structured log | [evidence/04-structured-log.png](evidence/04-structured-log.png) |
| PII redaction | [evidence/05-pii-redaction.png](evidence/05-pii-redaction.png) |
| Trace list | [evidence/06-trace-list.png](evidence/06-trace-list.png), [evidence/06-trace-list(bonus).png](evidence/06-trace-list(bonus).png) |
| Trace waterfall | [evidence/07-trace-waterfall.png](evidence/07-trace-waterfall.png) |
| Trace metadata | [evidence/08-trace-metadata.png](evidence/08-trace-metadata.png) |
| Prompt versions | [evidence/09-prompt-versions.png](evidence/09-prompt-versions.png) |
| Prompt rollback | [evidence/10-prompt-rollback.png](evidence/10-prompt-rollback.png) |
| Dashboard runtime | [evidence/11-dashboard-overview.png](evidence/11-dashboard-overview.png) |
| Incident metric | [evidence/12-incident-metric.png](evidence/12-incident-metric.png) |
| Incident log | [evidence/13-incident-log.png](evidence/13-incident-log.png) |
| Incident trace | [evidence/14-incident-trace.png](evidence/14-incident-trace.png) |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | 80/100 (Thiếu Correlation ID / PII) | 100/100 | Đạt điểm tối đa sau khi hoàn thiện middleware & PII scrubbing |
| `validate_dashboard.py` | 6/6 | 6/6 | Hợp lệ 100% theo contract `config/dashboard.yaml` |
| `pytest` | 22/22 passed | 22/22 passed | 100% Unit tests trôi chảy |
| Số traces hợp lệ | 0 | 10+ traces | Đã tạo thành công trên project Langfuse Cloud cá nhân |
| Số PII leak | 1 (email/phone thô) | 0 (đã scrub 100%) | Đã che hoàn toàn email, SĐT VN, CCCD và thẻ tín dụng |
| Latency P95 / TTFT P95 | ~160ms / ~55ms | ~160ms / ~55ms (Bình thường), ~4000ms (Khi gặp Incident) | Latency tăng vọt khi bật incident `rag_slow` |
| Retrieval success rate | 100% | 100% (Bình thường) | Hoạt động ổn định |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** `CorrelationIdMiddleware` trích xuất `x-request-id` từ header nếu có format `req-`, nếu không có sẽ sinh mới bằng `req-<8-hex>`. Sau đó dùng `clear_contextvars()` và `bind_contextvars(correlation_id=...)` gán vào structlog, đồng thời trả về response headers `x-request-id` và `x-response-time-ms`.
- **Các metadata được ghi vào structured log:** `service`, `env`, `feature`, `model`, `session_id`, `user_id_hash` (mã hóa SHA256 12 ký tự), `latency_ms`, `ttft_ms`, `tokens_in`, `tokens_out`, `cost_usd`, `quality_score`.
- **Cách bảo đảm PII được scrub trước khi ghi:** Đăng ký bộ xử lý `scrub_event` trong chuỗi `processors` của `structlog` **trước** `JsonlFileProcessor` và `JSONRenderer`. Hàm `scrub_text` dùng Regex thay thế toàn bộ email (`[REDACTED_EMAIL]`), SĐT Việt Nam (`[REDACTED_PHONE_VN]`), CCCD (`[REDACTED_CCCD]`), thẻ tín dụng (`[REDACTED_CREDIT_CARD]`).
- **Cách kiểm chứng kết quả:** Chạy `python scripts/validate_logs.py` đạt **100/100**, kiểm tra file `data/logs.jsonl` không còn bất kỳ dữ liệu nhạy cảm thô nào.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:** Traces hiển thị trong đúng Project `day13-k4-l3a-2A202602435` trên Langfuse Cloud, kết nối với log bằng đúng mã `correlation_id`.
- **Cấu trúc root/retrieval/generation observations:**
  - Root observation: `lab-agent-run` (as_type: agent)
  - Child Span 1: `retrieved-documents` (as_type: span) bọc hàm `retrieve()`
  - Child Generation 2: `llm-generate` (as_type: generation) bọc hàm `FakeLLM.generate()`, nhận `model`, `input`, `output` và `usage_details` (tokens_in, tokens_out).
- **Cách nối trace với log:** Thông qua `correlation_id` được gán vào metadata của trace bằng `propagate_attributes(...)`.
- **Prompt name:** `day13-chat`
- **Version/label baseline:** Version 1 (`baseline`, `production`)
- **Version/label candidate:** Version 2 (`candidate`)
- **Trace ID của mỗi version:**
  - Baseline (v1): Correlation ID `req-508baaea`
  - Candidate (v2): Correlation ID `req-ca56e089`
- **Cách promote và rollback `production`:** Sử dụng Langfuse SDK / UI gán nhãn `production` từ v1 sang v2 (Promote), sau đó gán lại nhãn `production` về Version 1 (Rollback).

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:** Xây dựng ứng dụng `scripts/dashboard.py` trực quan hóa 6 panel từ `data/logs.jsonl`: Latency (P50/P95/P99, TTFT), Traffic (req/min), Errors & RAG Success %, Cost (USD), Tokens (in/out), Quality Proxy.
- **SLO và lý do chọn:** Primary SLO `fast_successful_requests` yêu cầu 99.5% request đạt latency <= 3000ms trong 28 ngày. Ngưỡng 3000ms hợp lý vì baseline bình thường chỉ ~160ms, 3000ms đóng vai trò guardrail phát hiện tail latency trễ do RAG hoặc LLM.
- **Cách tính error budget:** Với lưu lượng 100,000 requests / 28 ngày và SLO 99.5%, Error Budget cho phép là 0.5%, tương đương tối đa 500 requests vi phạm. Nếu vượt quá 500 requests, Error Budget cạn kiệt và phải dừng phát triển tính năng mới.
- **Ba alert và runbook tương ứng:**
  1. `HighTailLatencyP95` (Warning, `latency_p95_ms > 3000` trong 5m) -> Runbook: [docs/alerts.md#alert-1](file:///Users/nguyenthutrang/Desktop/Vin/K4-L3-DAY13-NguyenThuTrang-2A202602435-Monitoring-LLMOps/docs/alerts.md#alert-1)
  2. `HighErrorRateSpike` (Critical, `error_rate_pct > 2` trong 3m) -> Runbook: [docs/alerts.md#alert-2](file:///Users/nguyenthutrang/Desktop/Vin/K4-L3-DAY13-NguyenThuTrang-2A202602435-Monitoring-LLMOps/docs/alerts.md#alert-2)
  3. `LowRetrievalSuccessRate` (Critical, `retrieval_success_rate_pct < 90` trong 5m) -> Runbook: [docs/alerts.md#alert-3](file:///Users/nguyenthutrang/Desktop/Vin/K4-L3-DAY13-NguyenThuTrang-2A202602435-Monitoring-LLMOps/docs/alerts.md#alert-3)

## 7. Điều tra challenge

- **Challenge ID:** `day13-k4-l3a-monitoring-llmops-v1`
- **Khoảng thời gian điều tra:** 10:04 – 10:06 29/09/2026
- **Triệu chứng từ metrics:** Panel Latency P95 tăng vọt lên `4043ms` cho feature `monitoring`, vượt quá ngưỡng SLO 3000ms và threshold challenge 2000ms.
- **Log line và correlation ID liên quan:** `req-38ed9b03` (Latency: 4043ms) và `req-d7ad3b7d` (Latency: 2664ms) trong `data/logs.jsonl`.
- **Trace ID và span gây ảnh hưởng:** Trace chứa Correlation ID `req-38ed9b03`, Child Span `retrieved-documents` (`retrieve()`) bị chậm chiếm tới ~4.0 giây trong tổng thời gian xử lý.
- **Root cause:** Sự cố nghẽn độ trễ tại RAG Vector Store khi truy xuất dữ liệu domain (Incident `rag_slow`).
- **Fix Action:** Cấu hình Query Caching cho các truy vấn phổ biến, tối ưu hóa Vector Index Search và giảm số lượng tài liệu `top_k` lấy về.
- **Preventive Measure:** Thiết lập Timeout tối đa cho RAG retrieval span (ví dụ max 1000ms), nếu quá thời gian sẽ tự động fallback sang tài liệu cố định để bảo vệ tổng thời gian phản hồi của API.

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:** Đăng ký bộ xử lý PII scrubbing (`scrub_event`) ở cấp độ `structlog` trước khi serialize JSON và ghi xuống file, đảm bảo dữ liệu nhạy cảm được che triệt để tại mọi nơi trong ứng dụng.
- **Một lỗi/blocker đã gặp:** Chạy test gặp lỗi `ModuleNotFoundError` do Terminal kích hoạt nhầm môi trường `.venv-1`.
- **Cách tìm nguyên nhân và xử lý:** Kiểm tra `pip list` giữa hai môi trường và chuyển lại đúng `.venv` chuẩn đã cài đầy đủ `requirements.txt`.
- **Cách hiểu luồng Metrics → Logs → Traces:** Metrics phát hiện triệu chứng tổng quan (ví dụ P95 spike) $\rightarrow$ Logs lọc các request cụ thể bị ảnh hưởng để lấy `correlation_id` $\rightarrow$ Traces dùng `correlation_id` để mở biểu đồ Waterfall định vị chính xác Child Span gây nghẽn.
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:** Giúp theo dõi chi phí từng câu hỏi, đánh giá chất lượng phản hồi và chủ động rollback về phiên bản prompt ổn định ngay lập tức khi phát hiện prompt mới suy giảm chất lượng.
- **Điều quan trọng nhất đã học:** Cách xây dựng hệ thống Observability toàn diện cho ứng dụng LLMOps theo tiêu chuẩn sản xuất (Production-ready).
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:** Cần bổ sung thêm bộ nhớ đệm Redis thực tế cho RAG vector retrieval.

## 9. Checklist trước khi nộp

- [x] Kết quả và evidence thuộc commit SHA cuối.
- [x] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [x] Incident evidence nối đúng metric → log → trace.
- [x] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [x] Repository chạy lại được theo README.
- [x] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [x] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
