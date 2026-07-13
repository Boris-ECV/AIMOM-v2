# Lock Directory
# 此資料夾存放工單認領 lock files，格式：TASK-XXX.lock
#
# Lock file 內容格式：
#   session: session-{timestamp}
#   task: TASK-XXX
#   locked_at: YYYY-MM-DDTHH:mm:ss
#   agent: ba-agent
#   released: false | true
#
# 規則：
# - Orchestrator 認領工單時立即建立 lock file
# - DevOps Agent 完成後標記 released: true
# - 下次啟動前可清理所有 released 的 lock files
