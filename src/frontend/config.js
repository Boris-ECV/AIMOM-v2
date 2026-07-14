// AIMOM 前端環境設定（TASK-014）
// 不同部署環境（dev/staging/prod）只需要改這個檔案，不用動 index.html。
window.APP_CONFIG = {
  apiBaseUrl: 'https://0e4wrwqj2g.execute-api.ap-northeast-1.amazonaws.com',
  cognitoDomain: 'aimom-dev-auth.auth.ap-northeast-1.amazoncognito.com',
  cognitoClientId: '3c1p876tadpdrd71uu2d982ei',
  // 必須與 infra/terraform.tfvars 的 frontend_callback_urls / frontend_logout_urls 一致
  redirectUri: 'https://d11d8l4nxw1bow.cloudfront.net',
  logoutUri: 'https://d11d8l4nxw1bow.cloudfront.net',
  region: 'ap-northeast-1',
};
