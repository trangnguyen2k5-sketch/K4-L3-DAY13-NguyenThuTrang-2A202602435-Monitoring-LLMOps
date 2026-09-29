# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert 1

- **Tên**: HighTailLatencyP95
- **Severity**: warning
- **Duration**: 5m
- **Kênh thông báo**: Slack (`#alerts-monitoring`)
- **SLI/SLO liên quan**: Primary SLO `fast_successful_requests` (Latency P95 ≤ 3000ms)
- **Điều kiện và thời gian duy trì**: `latency_p95_ms > 3000` liên tục trong 5 phút.
- **Ảnh hưởng tới người dùng**: Người dùng gặp hiện tượng trễ khi gửi câu hỏi cho AI Agent, thời gian nhận phản hồi bị chậm quá 3 giây.
- **Ba bước kiểm tra đầu tiên**:
  1. Mở Dashboard kiểm tra panel **Latency Percentiles & TTFT** để xác định độ trễ nằm ở RAG Retrieval (`retrieve()`) hay LLM Generation (`FakeLLM.generate()`).
  2. Lọc file log `data/logs.jsonl` tìm các bản ghi `response_sent` có `latency_ms > 3000` và trích xuất `correlation_id`.
  3. Tra cứu `correlation_id` trên Langfuse Cloud để kiểm tra biểu đồ Waterfall của Trace và khoanh vùng Child Span bị nghẽn.
- **Mitigation tạm thời**:
  - Nếu do RAG Vector Store chậm: Kích hoạt chế độ Caching kết quả truy vấn hoặc giảm tạm thời số lượng văn bản `top_k`.
  - Nếu do LLM generation: Cấu hình `max_tokens` nhỏ hơn hoặc chuyển tạm sang model fallback có latency thấp hơn.
- **Owner**: devops-oncall

---

## Alert 2

- **Tên**: HighErrorRateSpike
- **Severity**: critical
- **Duration**: 3m
- **Kênh thông báo**: Slack (`#alerts-critical`)
- **SLI/SLO liên quan**: Guardrail `error_rate_pct_max <= 2%`
- **Điều kiện và thời gian duy trì**: `error_rate_pct > 2%` liên tục trong 3 phút.
- **Ảnh hưởng tới người dùng**: Người dùng bị nhận lỗi HTTP 500 / Internal Server Error, không nhận được câu trả lời từ ứng dụng.
- **Ba bước kiểm tra đầu tiên**:
  1. Kiểm tra Dashboard panel **Error Rate & Retrieval Success** để xem tỷ lệ lỗi và phân loại `error_type` (ví dụ: `RuntimeError`, `TimeoutError`).
  2. Quét log `data/logs.jsonl` tìm các sự kiện `request_failed` và xem chi tiết lỗi trong `payload.detail`.
  3. Kiểm tra xem có Incident nào đang kích hoạt (`python scripts/inject_incident.py`) hoặc dịch vụ phụ thuộc nào bị sập hay không.
- **Mitigation tạm thời**:
  - Bật cơ chế Fallback trả về câu trả lời mặc định khi dịch vụ phụ thuộc gặp lỗi.
  - Khởi động lại API container/service nếu phát hiện hiện tượng tràn bộ nhớ hoặc treo thread pool.
- **Owner**: devops-oncall

---

## Alert 3

- **Tên**: LowRetrievalSuccessRate
- **Severity**: critical
- **Duration**: 5m
- **Kênh thông báo**: Slack (`#alerts-rag`)
- **SLI/SLO liên quan**: Guardrail `retrieval_success_rate_pct_min >= 90%`
- **Điều kiện và thời gian duy trì**: `retrieval_success_rate_pct < 90%` liên tục trong 5 phút.
- **Ảnh hưởng tới người dùng**: Câu trả lời từ AI Agent bị giảm chất lượng, thiếu thông tin ngữ cảnh tài liệu doanh nghiệp hoặc sử dụng thông tin fallback chung chung.
- **Ba bước kiểm tra đầu tiên**:
  1. Kiểm tra trạng thái kết nối tới Vector Database / RAG Corpus store.
  2. Lọc log `data/logs.jsonl` tìm sự kiện có `tool_name == "retrieval"` và `tool_success == False`.
  3. Kiểm tra log hệ thống RAG để tìm nguyên nhân timeout hoặc lỗi kết nối chỉ mục.
- **Mitigation tạm thời**:
  - Chuyển hướng RAG sang kho dữ liệu dự phòng (Read Replica / Backup Vector DB).
  - Sử dụng prompt local fallback mà không cần truy xuất dữ liệu động tạm thời.
- **Owner**: rag-team
