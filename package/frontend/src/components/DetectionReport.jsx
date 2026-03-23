import React, { useState, useRef } from 'react';
import { Shield, AlertTriangle, CheckCircle, Loader, ChevronDown, ChevronUp, Zap, Info, FileText, Upload, X } from 'lucide-react';
import toast from 'react-hot-toast';
import { detectionAPI, uploadAPI } from '../api';

// ─── 辅助函数 ────────────────────────────────────────────

const tierColor = (tier) => ({
  significant: { bg: 'bg-red-50',    border: 'border-red-200',   text: 'text-red-700',    ring: '#ef4444' },
  suspected:   { bg: 'bg-orange-50', border: 'border-orange-200',text: 'text-orange-700', ring: '#f97316' },
  unmarked:    { bg: 'bg-green-50',  border: 'border-green-200', text: 'text-green-700',  ring: '#22c55e' },
}[tier] || { bg: 'bg-gray-50', border: 'border-gray-200', text: 'text-gray-700', ring: '#6b7280' });

const tierBadge = (tier) => ({
  significant: 'bg-red-100 text-red-700 border-red-200',
  suspected:   'bg-orange-100 text-orange-700 border-orange-200',
  unmarked:    'bg-green-100 text-green-700 border-green-200',
  skip:        'bg-gray-100 text-gray-400 border-gray-200',
}[tier] || 'bg-gray-100 text-gray-500 border-gray-200');

const tierCnLabel = (tier) => ({
  significant: '显著疑似', suspected: '疑似', unmarked: '未标记', skip: '段落过短',
}[tier] || tier);

const featureBarColor = (risk) => {
  if (risk >= 0.65) return 'bg-red-500';
  if (risk >= 0.40) return 'bg-orange-400';
  return 'bg-green-500';
};

const riskLabel = (risk) => {
  if (risk >= 0.65) return { text: '高风险', cls: 'text-red-600' };
  if (risk >= 0.40) return { text: '中等',   cls: 'text-orange-600' };
  return { text: '正常', cls: 'text-green-600' };
};

// ─── 得分圆环 ─────────────────────────────────────────────

const ScoreRing = ({ score, tier }) => {
  const colors = tierColor(tier);
  const radius = 44;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;

  return (
    <svg width="120" height="120" viewBox="0 0 120 120">
      <circle cx="60" cy="60" r={radius} fill="none" stroke="#e5e7eb" strokeWidth="10" />
      <circle
        cx="60" cy="60" r={radius}
        fill="none"
        stroke={colors.ring}
        strokeWidth="10"
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        transform="rotate(-90 60 60)"
        style={{ transition: 'stroke-dashoffset 0.8s ease' }}
      />
      <text x="60" y="58" textAnchor="middle" fontSize="24" fontWeight="bold" fill={colors.ring}>{score}</text>
      <text x="60" y="74" textAnchor="middle" fontSize="11" fill="#6b7280">/ 100</text>
    </svg>
  );
};

// ─── 主组件 ──────────────────────────────────────────────

const cnkiTierColor = (tier) => ({
  significant: { bg: 'bg-red-50',    text: 'text-red-700',    badge: 'bg-red-100 text-red-700 border-red-200',    bar: 'bg-red-500' },
  suspected:   { bg: 'bg-orange-50', text: 'text-orange-700', badge: 'bg-orange-100 text-orange-700 border-orange-200', bar: 'bg-orange-400' },
}[tier] || { bg: 'bg-gray-50', text: 'text-gray-600', badge: 'bg-gray-100 text-gray-500 border-gray-200', bar: 'bg-gray-400' });

const cnkiTierLabel = (tier) => ({ significant: '显著疑似 (红色)', suspected: '疑似 (橙色)' }[tier] || tier);

const DetectionReport = ({ text }) => {
  const [report, setReport]           = useState(null);
  const [loading, setLoading]         = useState(false);
  const [useLlm, setUseLlm]           = useState(true);
  const [useCurvature, setUseCurvature] = useState(true);
  const [showSections, setShowSections]   = useState(false);
  const [showFragments, setShowFragments] = useState(true);
  const [showFeatures, setShowFeatures]   = useState(true);
  const [showExplanations, setShowExplanations] = useState(false);

  // CNKI 报告解析
  const [cnkiReport, setCnkiReport]     = useState(null);
  const [cnkiLoading, setCnkiLoading]   = useState(false);
  const [showCnkiFragments, setShowCnkiFragments] = useState(true);
  const cnkiFileRef = useRef(null);

  const runDetection = async () => {
    if (!text || text.length < 20) {
      toast.error('文本过短，无法检测');
      return;
    }
    try {
      setLoading(true);
      setReport(null);
      const resp = await detectionAPI.analyze(text, useLlm, useCurvature);
      setReport(resp.data);
    } catch (err) {
      toast.error('检测失败：' + (err.response?.data?.detail || '网络错误'));
    } finally {
      setLoading(false);
    }
  };

  const uploadCnkiReport = async (file) => {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      toast.error('请上传 PDF 格式的知网检测报告');
      return;
    }
    try {
      setCnkiLoading(true);
      setCnkiReport(null);
      const resp = await uploadAPI.parseCnkiReport(file);
      setCnkiReport(resp.data);
      toast.success(`报告解析成功，共 ${resp.data.flagged_fragments?.length ?? 0} 个标色片段`);
    } catch (err) {
      toast.error('解析失败：' + (err.response?.data?.detail || '文件格式不支持或非知网报告'));
    } finally {
      setCnkiLoading(false);
      if (cnkiFileRef.current) cnkiFileRef.current.value = '';
    }
  };

  const colors = report ? tierColor(report.document_tier) : null;
  const meta   = report?.report_metadata ?? {};

  return (
    <div className="space-y-5">
      {/* 检测控制栏 */}
      <div className="bg-white rounded-2xl shadow-ios p-5">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div>
            <h3 className="text-[17px] font-bold text-black">AIGC 风险筛查</h3>
            <p className="text-[13px] text-ios-gray mt-0.5">
              对改写后的文本进行多维风险评估，辅助判断是否值得提交知网检测
            </p>
          </div>

          <div className="flex items-center gap-3 flex-wrap">
            {/* LLM 开关 */}
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <div
                onClick={() => setUseLlm(v => !v)}
                className={`relative w-10 h-6 rounded-full transition-colors ${useLlm ? 'bg-ios-blue' : 'bg-gray-300'}`}
              >
                <div className={`absolute top-1 w-4 h-4 bg-white rounded-full shadow transition-transform ${useLlm ? 'translate-x-5' : 'translate-x-1'}`} />
              </div>
              <span className="text-[13px] text-ios-gray">
                LLM 评分<span className="text-[11px] ml-1 text-ios-gray/60">（更准，耗少量额度）</span>
              </span>
            </label>

            {/* 曲率开关 */}
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <div
                onClick={() => setUseCurvature(v => !v)}
                className={`relative w-10 h-6 rounded-full transition-colors ${useCurvature ? 'bg-purple-500' : 'bg-gray-300'}`}
              >
                <div className={`absolute top-1 w-4 h-4 bg-white rounded-full shadow transition-transform ${useCurvature ? 'translate-x-5' : 'translate-x-1'}`} />
              </div>
              <span className="text-[13px] text-ios-gray">
                概率曲率<span className="text-[11px] ml-1 text-ios-gray/60">（Fast-DetectGPT）</span>
              </span>
            </label>

            <button
              onClick={runDetection}
              disabled={loading || !text}
              className="flex items-center gap-2 bg-ios-blue hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed text-white font-semibold py-2 px-5 rounded-xl transition-all active:scale-[0.98] text-[15px]"
            >
              {loading ? (
                <><Loader className="w-4 h-4 animate-spin" />检测中...</>
              ) : (
                <><Shield className="w-4 h-4" />开始检测</>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* 知网报告解析区 */}
      <div className="bg-white rounded-2xl shadow-ios p-5">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div>
            <h3 className="text-[17px] font-bold text-black flex items-center gap-2">
              <FileText className="w-5 h-5 text-orange-500" />
              知网检测报告解析
            </h3>
            <p className="text-[13px] text-ios-gray mt-0.5">
              上传知网 AIGC 全文报告单（PDF），自动提取标红/橙的高风险段落
            </p>
          </div>
          <div className="flex items-center gap-3">
            <input
              ref={cnkiFileRef}
              type="file"
              accept=".pdf"
              className="hidden"
              onChange={(e) => uploadCnkiReport(e.target.files?.[0])}
            />
            <button
              onClick={() => cnkiFileRef.current?.click()}
              disabled={cnkiLoading}
              className="flex items-center gap-2 bg-orange-500 hover:bg-orange-600 disabled:bg-gray-300 disabled:cursor-not-allowed text-white font-semibold py-2 px-5 rounded-xl transition-all active:scale-[0.98] text-[15px]"
            >
              {cnkiLoading ? (
                <><Loader className="w-4 h-4 animate-spin" />解析中...</>
              ) : (
                <><Upload className="w-4 h-4" />上传报告</>
              )}
            </button>
            {cnkiReport && (
              <button
                onClick={() => setCnkiReport(null)}
                className="p-2 text-ios-gray hover:text-red-500 transition-colors"
                title="清除报告"
              >
                <X className="w-5 h-5" />
              </button>
            )}
          </div>
        </div>

        {/* 报告解析结果 */}
        {cnkiReport && (
          <div className="mt-5 space-y-4">
            {/* 元信息 + 总览 */}
            <div className="bg-orange-50 border border-orange-200 rounded-xl p-4 space-y-3">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-[13px]">
                <div>
                  <p className="text-ios-gray">论文标题</p>
                  <p className="font-semibold text-black truncate" title={cnkiReport.metadata.title}>
                    {cnkiReport.metadata.title || '—'}
                  </p>
                </div>
                <div>
                  <p className="text-ios-gray">作者</p>
                  <p className="font-semibold text-black">{cnkiReport.metadata.author || '—'}</p>
                </div>
                <div>
                  <p className="text-ios-gray">检测时间</p>
                  <p className="font-semibold text-black">{cnkiReport.metadata.detection_time || '—'}</p>
                </div>
                <div>
                  <p className="text-ios-gray">报告编号</p>
                  <p className="font-semibold text-black text-[11px]">{cnkiReport.metadata.report_no || '—'}</p>
                </div>
              </div>
              <div className="flex items-center gap-6 pt-2 border-t border-orange-200 flex-wrap text-[13px]">
                <div>
                  <span className="text-ios-gray">总字数：</span>
                  <span className="font-semibold">{cnkiReport.summary.total_chars?.toLocaleString() ?? '—'}</span>
                </div>
                <div>
                  <span className="text-ios-gray">疑似AI字数：</span>
                  <span className="font-bold text-red-600">{cnkiReport.summary.ai_chars?.toLocaleString() ?? '—'}</span>
                </div>
                <div>
                  <span className="text-ios-gray">AI率：</span>
                  <span className={`font-bold ${(cnkiReport.summary.ai_ratio ?? 0) >= 0.1 ? 'text-red-600' : 'text-green-600'}`}>
                    {cnkiReport.summary.ai_ratio != null ? `${(cnkiReport.summary.ai_ratio * 100).toFixed(1)}%` : '—'}
                  </span>
                </div>
                <div>
                  <span className="text-ios-gray">标色片段：</span>
                  <span className="font-bold text-orange-600">{cnkiReport.flagged_fragments.length} 处</span>
                </div>
              </div>
            </div>

            {/* 标色片段列表 */}
            {cnkiReport.flagged_fragments.length > 0 && (
              <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
                <button
                  onClick={() => setShowCnkiFragments(v => !v)}
                  className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-50 transition-colors"
                >
                  <span className="text-[14px] font-semibold text-black">
                    标色高风险片段（{cnkiReport.flagged_fragments.length} 处）
                  </span>
                  {showCnkiFragments ? <ChevronUp className="w-4 h-4 text-ios-gray" /> : <ChevronDown className="w-4 h-4 text-ios-gray" />}
                </button>
                {showCnkiFragments && (
                  <div className="border-t border-gray-100 divide-y divide-gray-50">
                    {cnkiReport.flagged_fragments.map((frag, i) => {
                      const tc = cnkiTierColor(frag.tier);
                      return (
                        <div key={i} className={`px-4 py-3 space-y-2 ${tc.bg}`}>
                          <div className="flex items-center justify-between gap-3 flex-wrap">
                            <div className="flex items-center gap-2">
                              <span className={`text-[11px] px-2 py-0.5 rounded-full border font-medium ${tc.badge}`}>
                                {cnkiTierLabel(frag.tier)}
                              </span>
                              {frag.ai_ratio > 0 && (
                                <span className={`text-[11px] font-semibold ${tc.text}`}>
                                  AI率 {(frag.ai_ratio * 100).toFixed(0)}%
                                </span>
                              )}
                            </div>
                            <span className="text-[11px] text-ios-gray">
                              第{frag.page}页 · {frag.char_count > 0 ? `${frag.char_count}字` : ''}
                            </span>
                          </div>
                          <p className="text-[13px] text-gray-800 leading-relaxed bg-white/70 rounded-lg px-3 py-2">
                            {frag.text}
                          </p>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

            {cnkiReport.flagged_fragments.length === 0 && (
              <div className="flex items-center gap-2 text-green-700 bg-green-50 border border-green-200 rounded-xl px-4 py-3 text-[13px]">
                <CheckCircle className="w-4 h-4 flex-shrink-0" />
                报告中未发现标色片段，文本当前通过知网检测
              </div>
            )}
          </div>
        )}
      </div>

      {/* 加载中 */}
      {loading && (
        <div className="bg-white rounded-2xl shadow-ios p-8 flex flex-col items-center gap-3">
          <Loader className="w-8 h-8 text-ios-blue animate-spin" />
          <p className="text-[15px] text-ios-gray">
            正在分析文体特征
            {useLlm ? '、LLM 评分' : ''}
            {useCurvature ? '、概率曲率（Fast-DetectGPT）' : ''}
            …
          </p>
        </div>
      )}

      {/* 报告主体 */}
      {report && !loading && (
        <div className="space-y-4">

          {/* ① 总览卡片 */}
          <div className={`rounded-2xl shadow-ios p-6 border ${colors.bg} ${colors.border}`}>
            <div className="flex items-start gap-6 flex-wrap">

              {/* 得分环 */}
              <div className="flex flex-col items-center gap-1">
                <ScoreRing score={report.document_score} tier={report.document_tier} />
                <span className={`text-[15px] font-bold ${colors.text}`}>{report.document_tier_cn}</span>
                <span className="text-[12px] text-ios-gray">
                  置信度：{
                    report.confidence === 'very_high' ? '非常高' :
                    report.confidence === 'high' ? '高' :
                    report.confidence === 'medium' ? '中' : '低'
                  }
                </span>
              </div>

              {/* 文字摘要 */}
              <div className="flex-1 min-w-[180px] space-y-3">
                <div>
                  <p className="text-[13px] text-ios-gray">AIGC 风险分</p>
                  <p className={`text-[28px] font-bold ${colors.text}`}>
                    {report.document_score} <span className="text-[14px] font-normal">/ 100</span>
                  </p>
                </div>
                <div className="grid grid-cols-2 gap-3 text-[13px]">
                  <div>
                    <p className="text-ios-gray">总字数</p>
                    <p className="font-semibold text-black">{meta.char_count?.toLocaleString() ?? '—'}</p>
                  </div>
                  <div>
                    <p className="text-ios-gray">风险字数</p>
                    <p className={`font-semibold ${meta.flagged_char_count > 0 ? colors.text : 'text-green-700'}`}>
                      {meta.flagged_char_count?.toLocaleString() ?? '—'}
                    </p>
                  </div>
                  <div>
                    <p className="text-ios-gray">章节数</p>
                    <p className="font-semibold text-black">{report.sections.length}</p>
                  </div>
                  <div>
                    <p className="text-ios-gray">检测耗时</p>
                    <p className="font-semibold text-black">{((meta.processing_time_ms ?? 0) / 1000).toFixed(1)}s</p>
                  </div>
                </div>
              </div>

              {/* LLM 信号 */}
              {report.llm?.available && report.llm.signals.length > 0 && (
                <div className="flex-1 min-w-[200px]">
                  <div className="flex items-center gap-1.5 mb-2">
                    <Zap className="w-4 h-4 text-ios-blue" />
                    <span className="text-[13px] font-semibold text-ios-blue">LLM 检测信号</span>
                    <span className="text-[11px] text-ios-gray ml-1">({report.llm.aigc_probability}%)</span>
                  </div>
                  <ul className="space-y-1.5">
                    {report.llm.signals.map((sig, i) => (
                      <li key={i} className="flex items-start gap-1.5 text-[13px] text-gray-700">
                        <AlertTriangle className="w-3.5 h-3.5 text-orange-500 flex-shrink-0 mt-0.5" />
                        {sig}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {!report.llm?.available && (
                <div className="text-[12px] text-ios-gray bg-white/60 rounded-lg px-3 py-2 self-start">
                  LLM 评分不可用（未配置 API 或已禁用）<br />
                  当前结果仅基于文体特征
                </div>
              )}

              {/* 概率曲率结果（Fast-DetectGPT Layer 3） */}
              {report.curvature?.available && (
                <div className="flex-1 min-w-[200px]">
                  <div className="flex items-center gap-1.5 mb-2">
                    <Zap className="w-4 h-4 text-purple-500" />
                    <span className="text-[13px] font-semibold text-purple-600">概率曲率检测</span>
                    <span className="text-[11px] text-ios-gray ml-1">Fast-DetectGPT</span>
                  </div>
                  <div className="space-y-1.5 text-[13px]">
                    <div className="flex items-center justify-between">
                      <span className="text-ios-gray">AI 风险概率</span>
                      <span className={`font-bold ${
                        report.curvature.ai_risk_percent >= 65 ? 'text-red-600' :
                        report.curvature.ai_risk_percent >= 40 ? 'text-orange-600' : 'text-green-600'
                      }`}>{report.curvature.ai_risk_percent}%</span>
                    </div>
                    <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className={`h-1.5 rounded-full transition-all duration-700 ${
                          report.curvature.ai_risk_percent >= 65 ? 'bg-red-500' :
                          report.curvature.ai_risk_percent >= 40 ? 'bg-orange-400' : 'bg-green-500'
                        }`}
                        style={{ width: `${report.curvature.ai_risk_percent}%` }}
                      />
                    </div>
                    <div className="flex justify-between text-[11px] text-ios-gray/70">
                      <span>归一化曲率：{report.curvature.normalized_curvature?.toFixed(3)}</span>
                      <span>token 数：{report.curvature.token_count}</span>
                    </div>
                  </div>
                </div>
              )}
              {report.curvature && !report.curvature.available && (
                <div className="text-[12px] text-ios-gray bg-white/60 rounded-lg px-3 py-2 self-start">
                  概率曲率不可用<br />
                  <span className="text-[11px]">{report.curvature.error || 'API 不支持 logprobs'}</span>
                </div>
              )}
            </div>

            {/* 免责说明 */}
            <div className="mt-4 pt-4 border-t border-current/10">
              <p className="text-[12px] text-ios-gray/80">
                ⚠️ 本结果为 AIGC 风险信号参考，不代表知网等商业系统的实际判定。建议风险分 ≥60 时手动修改后再提交检测。
              </p>
            </div>
          </div>

          {/* ② 片段证据列表 */}
          {report.fragments?.length > 0 && (
            <div className="bg-white rounded-2xl shadow-ios overflow-hidden">
              <button
                onClick={() => setShowFragments(v => !v)}
                className="w-full flex items-center justify-between p-5 hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <span className="text-[15px] font-bold text-black">风险片段证据</span>
                  <span className="text-[12px] text-ios-gray">
                    {report.fragments.filter(f => f.tier !== 'unmarked').length} 个疑似片段
                  </span>
                </div>
                {showFragments ? <ChevronUp className="w-5 h-5 text-ios-gray" /> : <ChevronDown className="w-5 h-5 text-ios-gray" />}
              </button>

              {showFragments && (
                <div className="border-t border-gray-100 divide-y divide-gray-50">
                  {report.fragments.slice(0, 10).map((frag, i) => (
                    <div key={i} className="px-5 py-4 space-y-2">
                      <div className="flex items-center justify-between gap-3">
                        <span className={`text-[11px] px-2 py-0.5 rounded-full border ${tierBadge(frag.tier)}`}>
                          {tierCnLabel(frag.tier)}
                        </span>
                        <span className={`text-[15px] font-bold ${
                          frag.tier === 'significant' ? 'text-red-600' :
                          frag.tier === 'suspected'   ? 'text-orange-600' : 'text-green-600'
                        }`}>{frag.score}分</span>
                      </div>
                      <p className="text-[13px] text-gray-700 leading-relaxed line-clamp-3 bg-gray-50 rounded-lg px-3 py-2">
                        {frag.text}
                      </p>
                      {frag.explanation?.summary && (
                        <p className="text-[12px] text-ios-gray flex items-start gap-1">
                          <Info className="w-3.5 h-3.5 flex-shrink-0 mt-0.5 text-ios-blue/70" />
                          {frag.explanation.summary}
                        </p>
                      )}
                    </div>
                  ))}
                  {report.fragments.length > 10 && (
                    <p className="text-center text-[12px] text-ios-gray py-3">
                      仅展示前10个片段，共 {report.fragments.length} 个
                    </p>
                  )}
                </div>
              )}
            </div>
          )}

          {/* ③ 章节风险分布 */}
          <div className="bg-white rounded-2xl shadow-ios overflow-hidden">
            <button
              onClick={() => setShowSections(v => !v)}
              className="w-full flex items-center justify-between p-5 hover:bg-gray-50 transition-colors"
            >
              <div className="flex items-center gap-3">
                <span className="text-[15px] font-bold text-black">章节风险分布</span>
                <div className="flex gap-2 text-[12px]">
                  {['significant', 'suspected', 'unmarked'].map(t => {
                    const cnt = report.sections.filter(s => s.tier === t).length;
                    if (cnt === 0) return null;
                    return (
                      <span key={t} className={`px-2 py-0.5 rounded-full border ${tierBadge(t)}`}>
                        {tierCnLabel(t)} ×{cnt}
                      </span>
                    );
                  })}
                </div>
              </div>
              {showSections ? <ChevronUp className="w-5 h-5 text-ios-gray" /> : <ChevronDown className="w-5 h-5 text-ios-gray" />}
            </button>

            {showSections && (
              <div className="border-t border-gray-100 divide-y divide-gray-50">
                {report.sections.filter(s => s.tier !== 'skip').map((sec, i) => (
                  <div key={i} className="flex items-start gap-3 px-5 py-3">
                    <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-gray-50 flex items-center justify-center text-[12px] font-bold text-ios-gray">
                      {i + 1}
                    </div>
                    <div className="flex-1 min-w-0">
                      {sec.title && (
                        <p className="text-[13px] font-semibold text-black mb-0.5">{sec.title}</p>
                      )}
                      <p className="text-[12px] text-gray-500 leading-relaxed line-clamp-2">{sec.text_preview}</p>
                      <div className="flex items-center gap-2 mt-1.5">
                        <span className={`text-[11px] px-2 py-0.5 rounded-full border ${tierBadge(sec.tier)}`}>
                          {sec.tier_cn}
                        </span>
                        {sec.score !== null && (
                          <span className="text-[11px] text-ios-gray">{sec.char_count}字 · 风险{sec.score}分</span>
                        )}
                      </div>
                    </div>
                    {sec.score !== null && (
                      <div className="flex-shrink-0 w-10 text-right">
                        <span className={`text-[15px] font-bold ${
                          sec.tier === 'significant' ? 'text-red-600' :
                          sec.tier === 'suspected'   ? 'text-orange-600' : 'text-green-600'
                        }`}>{sec.score}</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* ④ 文体特征详情 */}
          <div className="bg-white rounded-2xl shadow-ios overflow-hidden">
            <button
              onClick={() => setShowFeatures(v => !v)}
              className="w-full flex items-center justify-between p-5 hover:bg-gray-50 transition-colors"
            >
              <span className="text-[15px] font-bold text-black">文体特征分析</span>
              {showFeatures ? <ChevronUp className="w-5 h-5 text-ios-gray" /> : <ChevronDown className="w-5 h-5 text-ios-gray" />}
            </button>

            {showFeatures && (
              <div className="px-5 pb-5 space-y-4 border-t border-gray-100">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-4">
                  {Object.entries(report.stylometric.features).map(([key, feat]) => {
                    const rl = riskLabel(feat.risk);
                    return (
                      <div key={key} className="space-y-1.5">
                        <div className="flex justify-between items-center text-[13px]">
                          <span className="text-ios-gray">{feat.label}</span>
                          <span className={`font-semibold ${rl.cls}`}>{rl.text}</span>
                        </div>
                        <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                          <div
                            className={`h-2 rounded-full transition-all duration-700 ${featureBarColor(feat.risk)}`}
                            style={{ width: `${Math.round(feat.risk * 100)}%` }}
                          />
                        </div>
                        <div className="flex justify-between text-[11px] text-ios-gray/70">
                          <span>原始值：{feat.value}</span>
                          <span>风险：{Math.round(feat.risk * 100)}%</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
                <div className="flex gap-4 pt-2 flex-wrap text-[13px] text-ios-gray border-t border-gray-100">
                  <span>句子：{report.stylometric.stats.sentence_count}</span>
                  <span>段落：{report.stylometric.stats.paragraph_count}</span>
                  <span>词元：{report.stylometric.stats.token_count}</span>
                </div>
              </div>
            )}
          </div>

          {/* ⑤ 信号解释说明 */}
          {report.explanations?.length > 0 && (
            <div className="bg-white rounded-2xl shadow-ios overflow-hidden">
              <button
                onClick={() => setShowExplanations(v => !v)}
                className="w-full flex items-center justify-between p-5 hover:bg-gray-50 transition-colors"
              >
                <span className="text-[15px] font-bold text-black">信号解释说明</span>
                {showExplanations ? <ChevronUp className="w-5 h-5 text-ios-gray" /> : <ChevronDown className="w-5 h-5 text-ios-gray" />}
              </button>

              {showExplanations && (
                <div className="border-t border-gray-100 px-5 pb-5 pt-4 space-y-3">
                  {report.explanations.map((expl, i) => (
                    <div key={i} className="flex items-start gap-2 text-[13px]">
                      <AlertTriangle className="w-4 h-4 text-orange-400 flex-shrink-0 mt-0.5" />
                      <div>
                        <span className="font-semibold text-gray-800">{expl.label}</span>
                        {expl.summary && (
                          <p className="text-ios-gray mt-0.5">{expl.summary}</p>
                        )}
                      </div>
                    </div>
                  ))}
                  <p className="text-[11px] text-ios-gray/70 pt-2 border-t border-gray-100">
                    以上解释均来自实际触发的检测信号，不含推断性判断。
                  </p>
                </div>
              )}
            </div>
          )}

          {/* ⑥ 风险图例 */}
          <div className="bg-white rounded-2xl shadow-ios p-4 flex items-center gap-6 flex-wrap text-[12px] text-ios-gray">
            <span className="font-semibold text-black text-[13px]">风险图例</span>
            {Object.entries(report.risk_legend).map(([key, val]) => (
              <div key={key} className="flex items-center gap-1.5">
                <div className={`w-3 h-3 rounded-full ${
                  val.color === 'red' ? 'bg-red-500' :
                  val.color === 'orange' ? 'bg-orange-400' : 'bg-green-500'
                }`} />
                <span>{val.label}（≥{val.threshold}分）</span>
              </div>
            ))}
          </div>

        </div>
      )}
    </div>
  );
};

export default DetectionReport;
