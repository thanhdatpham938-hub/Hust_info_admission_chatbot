# Quy ước Commit — Conventional Commits 1.0.0

Tài liệu này quy định cách viết commit message trong dự án, dựa trên đặc tả [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/). Đặc tả gốc được cấp phép [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/). Bản dưới đây được dịch và biên soạn lại.

> **Ký hiệu trong tài liệu**
> - 📜 **Spec**: yêu cầu của đặc tả gốc.
> - 🧩 **Quy ước nhóm**: thực hành phổ biến mà dự án chọn áp dụng. Đặc tả không bắt buộc những điều này.

---

## 1. Vì sao dùng Conventional Commits

- Tự động sinh **CHANGELOG**.
- Tự động xác định mức tăng phiên bản theo [SemVer](https://semver.org/), dựa trên loại commit.
- Giúp đồng đội, người dùng và các bên liên quan hiểu bản chất của thay đổi.
- Kích hoạt quy trình build và publish.
- Giúp người mới dễ đóng góp hơn nhờ lịch sử commit có cấu trúc.

---

## 2. Cấu trúc

```
<type>[(scope)][!]: <description>

[body]

[footer(s)]
```

| Thành phần    | Bắt buộc | Mô tả |
|---------------|----------|-------|
| `type`        | ✅ | Danh từ chỉ loại thay đổi: `feat`, `fix`… |
| `scope`       | ❌ | Danh từ chỉ một phần của codebase, đặt trong ngoặc đơn: `fix(parser):` |
| `!`           | ❌ | Đặt **ngay trước** dấu `:` để báo breaking change |
| `: `          | ✅ | Dấu hai chấm và **một dấu cách** |
| `description` | ✅ | Tóm tắt ngắn thay đổi, nằm ngay sau `: ` |
| `body`        | ❌ | Giải thích thêm bối cảnh. Bắt đầu sau description **1 dòng trống** |
| `footer`      | ❌ | Một hoặc nhiều footer, bắt đầu sau body **1 dòng trống** |

---

## 3. Đặc tả chi tiết (16 quy tắc) 📜

Các từ **PHẢI**, **KHÔNG ĐƯỢC**, **NÊN** và **CÓ THỂ** được hiểu theo [RFC 2119](https://www.ietf.org/rfc/rfc2119.txt) (MUST, MUST NOT, SHOULD, MAY).

1. Commit **PHẢI** bắt đầu bằng một `type` (là danh từ, ví dụ `feat`, `fix`). Sau đó là `scope` (tùy chọn), `!` (tùy chọn), rồi **bắt buộc** có dấu `:` và một dấu cách.
2. **PHẢI** dùng `feat` khi commit thêm tính năng mới cho ứng dụng hoặc thư viện.
3. **PHẢI** dùng `fix` khi commit sửa một lỗi.
4. **CÓ THỂ** thêm `scope` sau `type`. Scope **PHẢI** là danh từ mô tả một phần của codebase và nằm trong ngoặc đơn, ví dụ `fix(parser):`.
5. `description` **PHẢI** đứng ngay sau `: `. Đây là phần tóm tắt ngắn về thay đổi.
6. **CÓ THỂ** có `body` dài hơn để cung cấp thêm bối cảnh. Body **PHẢI** bắt đầu sau description một dòng trống.
7. Body viết tự do và **CÓ THỂ** gồm nhiều đoạn, các đoạn cách nhau bằng dòng trống.
8. **CÓ THỂ** có một hoặc nhiều footer, đặt sau body một dòng trống. Mỗi footer **PHẢI** gồm một token (từ), rồi dấu phân cách `: ` hoặc ` #`, rồi giá trị. Định dạng này lấy cảm hứng từ [git trailer](https://git-scm.com/docs/git-interpret-trailers).
9. Token của footer **PHẢI** dùng `-` thay cho khoảng trắng, ví dụ `Acked-by`. Nhờ vậy footer phân biệt được với body nhiều đoạn. Ngoại lệ duy nhất là `BREAKING CHANGE` được phép có khoảng trắng.
10. Giá trị footer **CÓ THỂ** chứa khoảng trắng và xuống dòng. Trình phân tích dừng đọc một footer khi gặp cặp token + dấu phân cách hợp lệ tiếp theo.
11. Breaking change **PHẢI** được báo ở phần tiền tố `type/scope`, hoặc bằng một footer.
12. Nếu dùng footer, breaking change **PHẢI** viết là `BREAKING CHANGE` bằng chữ **HOA**, theo sau là `: ` và phần mô tả.
13. Nếu báo ở tiền tố, **PHẢI** đặt `!` ngay trước `:`. Khi đã dùng `!`, **CÓ THỂ** bỏ footer `BREAKING CHANGE:`. Khi đó description chính là mô tả breaking change.
14. **CÓ THỂ** dùng các type khác ngoài `feat` và `fix`, ví dụ `docs: update ref docs`.
15. Các thành phần của commit **KHÔNG ĐƯỢC** phân biệt hoa/thường khi công cụ xử lý. Riêng `BREAKING CHANGE` **PHẢI** viết hoa.
16. `BREAKING-CHANGE` là từ đồng nghĩa với `BREAKING CHANGE` khi dùng làm token trong footer.

---

## 4. Các `type`

| Type       | Ý nghĩa | SemVer |
|------------|---------|--------|
| `feat`     | Thêm tính năng mới | **MINOR** (1.**2**.0) |
| `fix`      | Sửa lỗi | **PATCH** (1.2.**1**) |
| `docs`     | Chỉ thay đổi tài liệu | — |
| `style`    | Định dạng code (khoảng trắng, dấu chấm phẩy…), không đổi logic | — |
| `refactor` | Tái cấu trúc, không thêm tính năng và không sửa lỗi | — |
| `perf`     | Cải thiện hiệu năng | — |
| `test`     | Thêm hoặc sửa test | — |
| `build`    | Hệ thống build, dependencies (npm, gradle, docker…) | — |
| `ci`       | Cấu hình CI/CD | — |
| `chore`    | Việc khác, không động tới src hay test | — |
| `revert`   | Hoàn tác commit trước đó | — |

- 📜 Đặc tả chỉ quy định hai type là `feat` và `fix`. Các type còn lại lấy theo [`@commitlint/config-conventional`](https://github.com/conventional-changelog/commitlint/tree/master/%40commitlint/config-conventional), vốn dựa trên quy ước của Angular.
- 📜 Các type ngoài `feat` và `fix` **không ảnh hưởng** tới SemVer, trừ khi commit có breaking change.
- 📜 Breaking change có thể xuất hiện ở commit thuộc **bất kỳ type nào** và luôn dẫn tới **MAJOR** (**2**.0.0).
- 📜 Nhóm được phép tự định nghĩa thêm type và thay đổi danh sách type theo thời gian.

---

## 5. Quy tắc viết của dự án 🧩

Các quy tắc sau là quy ước của nhóm, không phải yêu cầu của đặc tả.

**Header (dòng đầu)**
- Viết `type` bằng chữ thường, ví dụ `feat` chứ không phải `Feat`. Đặc tả cho phép viết hoa hay thường tùy ý, miễn là **nhất quán**.
- Viết `description` ở thể mệnh lệnh, thì hiện tại: `add`, `fix`, `update`. Không dùng `added` hay `fixes`.
- Không viết hoa chữ cái đầu của description và không kết thúc bằng dấu chấm.
- Toàn bộ header nên dài tối đa **72 ký tự**.
- Scope là danh từ ngắn, ví dụ `api`, `auth`, `ui`, `db`, `deps`.

**Body**
- Giải thích **lý do** và **bối cảnh** của thay đổi, không mô tả lại diff.
- Ngắt dòng ở khoảng 72–100 ký tự.

**Footer thường dùng**
- `Refs: #123` hoặc `Refs #123` để tham chiếu issue.
- `Closes #123` để đóng issue (GitHub và GitLab hiểu cú pháp này).
- `Reviewed-by: Tên`
- `Co-authored-by: Tên <email>`

---

## 6. Breaking change

**Cách 1: dùng `!`.** Description chính là mô tả breaking change.
```
feat(api)!: send an email to the customer when a product is shipped
```

**Cách 2: dùng footer.**
```
feat: allow provided config object to extend other configs

BREAKING CHANGE: `extends` key in config file is now used for extending other config files
```

**Cách 3: dùng cả hai.**
```
feat!: drop support for Node 6

BREAKING CHANGE: use JavaScript features not available in Node 6.
```

> `BREAKING CHANGE` phải viết HOA. Có thể dùng `BREAKING-CHANGE` thay thế.

---

## 7. Ví dụ

**Không có body**
```
docs: correct spelling of CHANGELOG
```

**Có scope**
```
feat(lang): add Polish language
```

**Body nhiều đoạn và nhiều footer**
```
fix: prevent racing of requests

Introduce a request id and a reference to latest request. Dismiss
incoming responses other than from latest request.

Remove timeouts which were used to mitigate the racing issue but are
obsolete now.

Reviewed-by: Z
Refs: #123
```

**Các type khác**
```
style: format code with prettier
refactor(user): extract validation into helper
perf(db): add index on orders.created_at
test(auth): add tests for token refresh
build(deps): bump axios from 1.6.0 to 1.7.2
ci: cache node_modules in github actions
chore: update .gitignore
```

**Viết bằng tiếng Việt (nếu nhóm dùng tiếng Việt)**
```
fix(payment): xử lý timeout từ cổng thanh toán

Cổng thanh toán đôi khi phản hồi quá 30 giây, khiến request bị treo
và đơn hàng kẹt ở trạng thái "pending". Thêm timeout 15 giây và
retry tối đa 3 lần.

Closes #142
```

**Revert.** Đặc tả khuyến nghị dùng type `revert` kèm footer `Refs` liệt kê SHA của các commit bị hoàn tác:
```
revert: let us never again speak of the noodle incident

Refs: 676104e, a215868
```

---

## 8. Nên / Không nên

| ❌ Không nên | ✅ Nên |
|-------------|-------|
| `update code` | `refactor(cart): simplify total calculation` |
| `Fix bug` | `fix(login): show error when password is empty` |
| `feat: Added new API.` | `feat(api): add product search endpoint` |
| `feat:add search` (thiếu dấu cách) | `feat: add search` |
| `feat (api): ...` (có dấu cách trước ngoặc) | `feat(api): ...` |
| `feat: ...!` hoặc `feat!(api):` | `feat(api)!:` (dấu `!` đặt ngay trước `:`) |
| `breaking change: ...` (viết thường) | `BREAKING CHANGE: ...` |
| `Reviewed by: Z` (token có khoảng trắng) | `Reviewed-by: Z` |
| Một commit gồm cả feat, fix và refactor | Tách thành nhiều commit, mỗi commit một mục đích |

---

## 9. FAQ

**Trong giai đoạn phát triển ban đầu thì viết commit thế nào?**
Hãy làm như thể sản phẩm đã phát hành. Luôn có người đang dùng phần mềm của bạn, dù chỉ là đồng nghiệp. Họ cần biết thay đổi nào sửa lỗi và thay đổi nào gây vỡ.

**Type viết hoa hay viết thường?**
Viết kiểu nào cũng được, miễn là nhất quán. Dự án này dùng chữ thường.

**Một commit thuộc nhiều type thì sao?**
Nếu có thể, hãy tách thành nhiều commit. Một lợi ích của chuẩn này là khiến commit và PR gọn gàng, có tổ chức hơn.

**Chuẩn này có làm chậm tốc độ phát triển không?**
Nó chỉ ngăn việc làm nhanh một cách lộn xộn. Về lâu dài, nó giúp nhóm đi nhanh hơn khi có nhiều dự án và nhiều người đóng góp.

**Có khiến nhóm bị bó buộc vào các type có sẵn không?**
Không. Nhóm có thể tự đặt type riêng và điều chỉnh danh sách type theo thời gian.

**Liên quan tới SemVer thế nào?**
- `fix` → **PATCH**
- `feat` → **MINOR**
- Commit có breaking change, bất kể type → **MAJOR**

**Lỡ dùng sai type thì sửa ra sao?**
- **Sai type nhưng type đó vẫn hợp lệ** (ví dụ dùng `fix` thay vì `feat`): nếu chưa merge hoặc release, dùng `git rebase -i` để sửa lịch sử. Nếu đã release, cách sửa phụ thuộc vào công cụ và quy trình của nhóm.
- **Type không có trong chuẩn** (ví dụ gõ nhầm `feet` thay vì `feat`): không nghiêm trọng. Commit đó chỉ bị các công cụ dựa trên chuẩn bỏ qua.

**Mọi người đóng góp đều phải dùng chuẩn này à?**
Không bắt buộc. Nếu nhóm dùng quy trình **squash merge**, maintainer có thể viết lại commit message cho đúng chuẩn khi merge PR. Người đóng góp không phải làm thêm việc gì.

**Xử lý commit revert thế nào?**
Đặc tả không quy định chi tiết, mà để các công cụ tự xử lý bằng type và footer. Khuyến nghị là dùng type `revert` kèm footer `Refs: <SHA>` (xem ví dụ ở mục 7).

---

## 10. Công cụ hỗ trợ (tùy chọn)

| Công cụ | Tác dụng |
|---------|----------|
| [commitlint](https://commitlint.js.org/) | Kiểm tra commit message có đúng chuẩn không |
| [husky](https://typicode.github.io/husky/) | Chạy commitlint qua git hook `commit-msg` |
| [commitizen](https://commitizen-tools.github.io/commitizen/) | Hỏi từng bước để tạo commit đúng chuẩn |
| [semantic-release](https://semantic-release.gitbook.io/) / [release-please](https://github.com/googleapis/release-please) | Tự động tăng version và sinh CHANGELOG |

**Cài nhanh commitlint và husky (Node.js):**
```bash
npm i -D @commitlint/cli @commitlint/config-conventional husky
echo "export default { extends: ['@commitlint/config-conventional'] };" > commitlint.config.js
npx husky init
echo "npx --no -- commitlint --edit \$1" > .husky/commit-msg
```

---

## 11. Tóm tắt nhanh

```
fix(scope): mô tả          → sửa lỗi          → PATCH
feat(scope): mô tả         → tính năng mới    → MINOR
type(scope)!: mô tả        → breaking change  → MAJOR
BREAKING CHANGE: mô tả     → breaking change  → MAJOR  (footer, viết HOA)
docs/style/refactor/...    → không đổi version (trừ khi có breaking change)
```

---

*Nguồn: [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/), CC BY 3.0.*