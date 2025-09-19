const serviceStatus = document.getElementById('service-status'); // 获取显示服务状态文本的元素
const uptimeBar = document.getElementById('uptime-bar'); // 获取可用率进度条元素
const uptimePercentage = document.getElementById('uptime-percentage'); // 获取可用率数值显示元素
const currentTimeElement = document.getElementById('current-time'); // 获取当前时间显示元素
const automationStatusElement = document.getElementById('automation-status'); // 获取自动脚本状态显示元素
const nextCheckElement = document.getElementById('next-check'); // 获取下一次巡检倒计时显示元素
const lastCheckElement = document.getElementById('last-check-time'); // 获取最近一次巡检时间显示元素
const currentYearElement = document.getElementById('current-year'); // 获取当前年份显示元素
const timelineList = document.getElementById('timeline-list'); // 获取运维节奏列表容器
const supportForm = document.getElementById('support-form'); // 获取支援表单元素
const supportHistoryList = document.getElementById('support-history'); // 获取支援记录列表容器
const toggleThemeButton = document.getElementById('toggle-theme'); // 获取主题切换按钮
const togglePanelButton = document.getElementById('toggle-panel'); // 获取浮动面板切换按钮
const floatingPanel = document.getElementById('floating-panel'); // 获取浮动面板容器
const panelStatusElement = document.getElementById('panel-status'); // 获取浮动面板状态文本
const panelTasksList = document.getElementById('panel-tasks'); // 获取浮动面板任务列表

const CHECK_INTERVAL = 15 * 60 * 1000; // 定义巡检间隔为15分钟
let nextCheckTimestamp = Date.now() + CHECK_INTERVAL; // 记录下一次巡检的时间戳
const SUPPORT_STORAGE_KEY = 'cloud-guard-support-history'; // 定义支援记录在本地存储中的键名

const timelineData = [ // 定义全天候运维节奏的数据数组开始
  { period: '00:00 - 06:00', focus: '夜间巡检', detail: '自动巡检脚本执行核心服务自检并生成摘要报告。' }, // 定义夜间运维任务
  { period: '06:00 - 12:00', focus: '内容同步', detail: '同步最新内容到GitHub Pages并验证静态资源缓存。' }, // 定义上午运维任务
  { period: '12:00 - 18:00', focus: '体验优化', detail: '监控访问性能并调优DNS与CDN策略，保障全球快速访问。' }, // 定义下午运维任务
  { period: '18:00 - 24:00', focus: '安全巡防', detail: '执行安全扫描与备份校验，更新零信任访问策略。' } // 定义晚间运维任务
]; // 定义全天候运维节奏的数据数组结束

let operationsTasks = [ // 定义浮动面板展示的运维任务数组开始
  { title: '全局可用性扫描', status: '每15分钟自动运行' }, // 定义第一个运维任务
  { title: 'GitHub Pages构建监控', status: '实时监听发布状态' }, // 定义第二个运维任务
  { title: '静态资源CDN刷新', status: '每日02:30例行刷新' } // 定义第三个运维任务
]; // 定义浮动面板展示的运维任务数组结束

function renderTimeline() { // 定义渲染运维节奏列表的函数开始
  timelineList.innerHTML = ''; // 清空原有列表内容
  timelineData.forEach((item) => { // 遍历每一项运维数据
    const listItem = document.createElement('li'); // 创建列表项元素
    listItem.className = 'timeline-item'; // 设置列表项的类名
    listItem.innerHTML = `<strong>${item.period}</strong> · ${item.focus}<br>${item.detail}`; // 组合显示时间段、重点与细节
    timelineList.appendChild(listItem); // 将列表项插入到列表容器中
  }); // 运维数据遍历结束
} // 渲染运维节奏列表的函数结束

function renderPanelTasks() { // 定义渲染浮动面板任务列表的函数开始
  panelTasksList.innerHTML = ''; // 清空原有任务列表
  operationsTasks.forEach((task) => { // 遍历运维任务数组
    const taskItem = document.createElement('li'); // 创建任务列表项元素
    taskItem.className = 'panel-task'; // 设置任务列表项的类名
    taskItem.innerHTML = `<strong>${task.title}</strong><br>${task.status}`; // 设置任务内容与状态描述
    panelTasksList.appendChild(taskItem); // 将任务列表项添加到面板中
  }); // 运维任务遍历结束
} // 渲染浮动面板任务列表的函数结束

function loadSupportHistory() { // 定义加载支援记录的函数开始
  const cached = localStorage.getItem(SUPPORT_STORAGE_KEY); // 从本地存储获取历史数据
  if (!cached) { // 判断是否存在缓存数据
    return []; // 如果没有缓存则返回空数组
  } // 判断缓存存在性的代码结束
  try { // 尝试解析缓存数据
    const parsed = JSON.parse(cached); // 将缓存字符串解析为对象数组
    return Array.isArray(parsed) ? parsed : []; // 如果解析结果是数组则返回数组否则返回空数组
  } catch (error) { // 捕获解析过程中的异常
    console.error('读取支援记录失败', error); // 在控制台打印错误信息
    return []; // 出现异常时返回空数组
  } // try-catch语句结束
} // 加载支援记录的函数结束

function saveSupportHistory(records) { // 定义保存支援记录的函数开始
  localStorage.setItem(SUPPORT_STORAGE_KEY, JSON.stringify(records)); // 将记录数组序列化后写入本地存储
} // 保存支援记录的函数结束

let supportRecords = loadSupportHistory(); // 读取本地存储中的支援记录并保存到变量

function renderSupportHistory() { // 定义渲染支援记录列表的函数开始
  supportHistoryList.innerHTML = ''; // 清空现有记录
  if (supportRecords.length === 0) { // 判断是否存在记录
    const emptyItem = document.createElement('li'); // 创建空状态列表项
    emptyItem.className = 'support-item'; // 设置空状态列表项的类名
    emptyItem.textContent = '暂无支援请求，系统运行稳定。'; // 设置空状态提示文本
    supportHistoryList.appendChild(emptyItem); // 将空状态项加入列表
    return; // 结束函数执行
  } // 空状态判断结束
  supportRecords.forEach((record) => { // 遍历每一条支援记录
    const recordItem = document.createElement('li'); // 创建记录列表项元素
    recordItem.className = 'support-item'; // 设置记录列表项的类名
    recordItem.innerHTML = `<strong>${record.requester}</strong> · ${record.contact}<br>${record.issue}<br><span>${record.time}</span>`; // 设置记录展示内容
    supportHistoryList.appendChild(recordItem); // 将记录项加入列表
  }); // 支援记录遍历结束
} // 渲染支援记录列表的函数结束

function calculateUptime(date) { // 定义计算可用率的函数开始
  const base = 99.97; // 定义基础可用率
  const variation = Math.sin(date.getTime() / 600000) * 0.02; // 使用正弦函数生成轻微波动值
  const uptime = Math.min(100, Math.max(99.8, base + variation)); // 将可用率限制在99.8%到100%之间
  return uptime.toFixed(2); // 返回保留两位小数的字符串
} // 计算可用率的函数结束

function updateOperationalStatus() { // 定义更新运行状态的函数开始
  const now = new Date(); // 获取当前时间
  const uptimeValue = calculateUptime(now); // 计算当前可用率
  const statusMessages = [ // 定义可能显示的状态消息数组开始
    '服务运行正常，所有节点响应迅速。', // 状态消息一
    '自动化巡检通过，未发现异常指标。', // 状态消息二
    '缓存命中率高，用户访问体验流畅。' // 状态消息三
  ]; // 定义可能显示的状态消息数组结束
  const messageIndex = now.getMinutes() % statusMessages.length; // 根据分钟数选择状态消息
  serviceStatus.textContent = statusMessages[messageIndex]; // 更新状态消息文本
  uptimeBar.style.width = `${uptimeValue}%`; // 设置进度条宽度反映可用率
  uptimePercentage.textContent = `${uptimeValue}%`; // 更新可用率文本
  currentTimeElement.textContent = now.toLocaleTimeString('zh-CN', { hour12: false }); // 更新北京时间显示
  const automationStates = [ // 定义自动脚本状态数组开始
    '自动脚本：内容同步中', // 自动脚本状态一
    '自动脚本：日志整理中', // 自动脚本状态二
    '自动脚本：巡检报告推送中' // 自动脚本状态三
  ]; // 定义自动脚本状态数组结束
  const automationIndex = now.getMinutes() % automationStates.length; // 根据分钟数选择自动脚本状态
  automationStatusElement.textContent = automationStates[automationIndex]; // 更新自动脚本状态显示
  let countdown = nextCheckTimestamp - now.getTime(); // 计算距离下一次巡检的毫秒数
  if (countdown <= 0) { // 判断是否已经到达巡检时间
    lastCheckElement.textContent = now.toLocaleTimeString('zh-CN', { hour12: false }); // 更新最近巡检时间为当前时间
    panelStatusElement.textContent = '最新巡检完成，一切正常。'; // 更新浮动面板状态文本
    operationsTasks.unshift({ title: '例行巡检回执', status: `${lastCheckElement.textContent} 已完成` }); // 将最新巡检结果添加到任务列表开头
    operationsTasks = operationsTasks.slice(0, 5); // 保持任务列表长度不超过五条
    renderPanelTasks(); // 重新渲染浮动面板任务列表
    nextCheckTimestamp = now.getTime() + CHECK_INTERVAL; // 重置下一次巡检时间戳
    countdown = nextCheckTimestamp - now.getTime(); // 重新计算倒计时
  } // 巡检时间判断结束
  const countdownMinutes = Math.floor(countdown / 60000); // 计算剩余分钟数
  const countdownSeconds = Math.floor((countdown % 60000) / 1000); // 计算剩余秒数
  const safeMinutes = countdownMinutes.toString().padStart(2, '0'); // 将分钟数格式化为两位数
  const safeSeconds = countdownSeconds.toString().padStart(2, '0'); // 将秒数格式化为两位数
  nextCheckElement.textContent = `${safeMinutes}分${safeSeconds}秒`; // 更新倒计时显示
} // 更新运行状态的函数结束

function startStatusLoop() { // 定义启动状态循环的函数开始
  updateOperationalStatus(); // 立即执行一次状态更新
  setInterval(updateOperationalStatus, 5000); // 每5秒更新一次状态信息
} // 启动状态循环的函数结束

function handleSupportSubmit(event) { // 定义处理支援表单提交的函数开始
  event.preventDefault(); // 阻止表单默认提交行为
  const formData = new FormData(supportForm); // 使用FormData收集表单数据
  const record = { // 定义新的支援记录对象开始
    requester: formData.get('requester') || '匿名用户', // 获取联系人姓名并提供默认值
    contact: formData.get('contact') || '未提供联系方式', // 获取联系方式并提供默认值
    issue: formData.get('issue') || '未填写需求详情', // 获取需求描述并提供默认值
    time: new Date().toLocaleString('zh-CN') // 记录提交时间
  }; // 定义新的支援记录对象结束
  supportRecords.unshift(record); // 将新的支援记录插入数组开头
  supportRecords = supportRecords.slice(0, 10); // 限制支援记录数量最多十条
  saveSupportHistory(supportRecords); // 将更新后的记录保存到本地存储
  renderSupportHistory(); // 重新渲染支援记录列表
  supportForm.reset(); // 重置表单清空输入
  panelStatusElement.textContent = '收到新的支援请求，已创建处理任务。'; // 更新浮动面板状态提示文本
  operationsTasks.unshift({ title: `支援：${record.requester}`, status: `${record.time} 待响应` }); // 在运维任务中新增支援事项
  operationsTasks = operationsTasks.slice(0, 5); // 控制运维任务列表长度
  renderPanelTasks(); // 重新渲染浮动面板任务列表
} // 处理支援表单提交的函数结束

function initThemeSwitcher() { // 定义初始化主题切换功能的函数开始
  toggleThemeButton.addEventListener('click', () => { // 为主题切换按钮绑定点击事件开始
    document.body.classList.toggle('dark-theme'); // 切换页面主体的深色主题类
    const isDark = document.body.classList.contains('dark-theme'); // 判断当前是否处于深色主题
    toggleThemeButton.textContent = isDark ? '切换到浅色' : '切换主题'; // 根据主题状态更新按钮文本
  }); // 主题切换按钮点击事件结束
} // 初始化主题切换功能的函数结束

function initFloatingPanel() { // 定义初始化浮动面板的函数开始
  togglePanelButton.addEventListener('click', () => { // 为面板切换按钮绑定点击事件开始
    floatingPanel.classList.toggle('active'); // 切换浮动面板的显示状态
    const isActive = floatingPanel.classList.contains('active'); // 判断浮动面板是否处于打开状态
    togglePanelButton.textContent = isActive ? '收起看板' : '运维看板'; // 根据面板状态更新按钮文本
  }); // 面板切换按钮点击事件结束
} // 初始化浮动面板的函数结束

function initializeApp() { // 定义初始化页面应用的函数开始
  currentYearElement.textContent = new Date().getFullYear(); // 设置当前年份显示
  lastCheckElement.textContent = new Date().toLocaleTimeString('zh-CN', { hour12: false }); // 初始化最近巡检时间
  renderTimeline(); // 渲染运维节奏列表
  renderPanelTasks(); // 渲染浮动面板任务列表
  renderSupportHistory(); // 渲染支援记录列表
  startStatusLoop(); // 启动运行状态循环
  initThemeSwitcher(); // 初始化主题切换功能
  initFloatingPanel(); // 初始化浮动面板功能
  supportForm.addEventListener('submit', handleSupportSubmit); // 为支援表单绑定提交事件
} // 初始化页面应用的函数结束

initializeApp(); // 调用初始化函数启动应用
