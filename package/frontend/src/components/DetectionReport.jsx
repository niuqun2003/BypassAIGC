import React, { useState } from 'react';
import { Shield, AlertTriangle, CheckCircle, Loader, ChevronDown, ChevronUp, Zap } from 'lucide-react';
import toast from 'react-hot-toast';
import { detectionAPI } from '../api';

// ─── 辅助函数 ────────────────────────────────────────────

const tierColor = (tier) => ({
  high:   { bg: 'bg-red-50',    border: 'border-red-200',   text: 'text-red-700',    bar: 'bg-red-500' },
  medium: { bg: 'bg-orange-50', border: 'border-orange-200',text: 'text-orange-700', bar: 'bg-orange-400' },
  low:    { bg: 'bg-green-50',  border: 'border-green-200', text: 'text-green-700',  bar: 'bg-green-500' },
}[tier] || { bg: 'bg-gray-50', border: 'border-gray-200', text: 'text-gray-700', bar: 'bg-gray-400' });

const sectionTierColor = (tier) => ({
  significant: 'bg-red-100 text-red-700 border-red-200',
  suspected:   'bg-orange-100 text-orange-700 border-orange-200',
  unmarked:    'bg-green-100 text-green-700 border-green-200',
  skip:        'bg-gray-100 text-gray-400 border-gray-200',
}[tier] || 'bg-gray-100 text-gray-500 border-gray-200');

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

  const ringColor = { high: '#ef4444', medium: '#f97316', low: '#22c55e' }[tier] || '#6b7280';

  return (
    <svg width="120" height="120" viewBox="0 0 120 120">
      <circle cx="60" cy="60" r={radius} fill="none" stroke="#e5e7eb" strokeWidth="10" />
      <circle
        cx="60" cy="60" r={radius}
        fill="none"
        stroke={ringColor}
        strokeWidth="10"
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        transform="rotate(-90 60 60)"
        style={{ transition: 'stroke-dashoffset 0.8s ease' }}
      />
      <text x="60" y="58" textAnchor="middle" fontSize="24" fontWeight="bold" fill={ringColor}>{score}</text>
      <text x="60" y="74" textAnchor="middle" fontSize="11" fill="#6b7280">/ 100</text>
    </svg>
  );
};

// ─── 主组件 ──────────────────────────────────────────────

const DetectionReport = ({ text }) => {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [useLlm, setUseLlm] = useState(true);
  const [showSections, setShowSections] = useState(false);
  const [showFeatures, setShowFeatures] = useState(true);

  const runDetection = async () => {
    if (!text || text.length < 20) {
      toast.error('文本过短，无法检测');
      return;
    }
    try {
      setLoading(true);
      setReport(null);
      const resp = await detectionAPI.analyze(text, useLlm);
      setReport(resp.data);
    } catch (err) {
      toast.error('检测失败：' + (err.response?.data?.detail || '网络错误'));
    } finally {
      setLoading(false);
    }
  };

  const colors = report ? tierColor(report.document_tier) : null;

  return (
    <div className="space-y-5">
      {/* 检测控制栏 */}
      <div className="bg-white rounded-2xl shadow-ios p-5">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div>
            <h3 className="text-[17px] font-bold text-black">AIGC 风险检测</h3>
            <p className="text-[13px] text-ios-gray mt-0.5">
              对改写后的文本进行 AIGC 含量评估，辅助判断是否值得提交知网检测
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
                LLM 增强<span className="text-[11px] ml-1 text-ios-gray/60">（更准，耗少量额度）</span>
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

      {/* 加载中 */}
      {loading && (
        <div className="bg-white rounded-2xl shadow-ios p-8 flex flex-col items-center gap-3">
          <Loader className="w-8 h-8 text-ios-blue animate-spin" />
          <p className="text-[15px] text-ios-gray">正在分析文体特征{useLlm ? '和 LLM 评分' : ''}…</p>
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
                  置信度：{report.confidence === 'high' ? '高' : report.confidence === 'medium' ? '中' : '低'}
                </span>
              </div>

              {/* 文字摘要 */}
              <div className="flex-1 min-w-[180px] space-y-3">
                <div>
                  <p className="text-[13px] text-ios-gray">AIGC 风险分</p>
                  <p className={`text-[28px] font-bold ${colors.text}`}>{report.document_score} <span className="text-[14px] font-normal">/ 100</span></p>
                </div>
                <div className="grid grid-cols-2 gap-3 text-[13px]">
                  <div>
                    <p className="text-ios-gray">总字数</p>
                    <p className="font-semibold text-black">{report.char_count.toLocaleString()}</p>
                  </div>
                  <div>
                    <p className="text-ios-gray">疑似AIGC字数</p>
                    <p className={`font-semibold ${report.flagged_char_count > 0 ? colors.text : 'text-green-700'}`}>
                      {report.flagged_char_count.toLocaleString()}
                    </p>
                  </div>
                  <div>
                    <p className="text-ios-gray">段落数</p>
                    <p className="font-semibold text-black">{report.stylometric.stats.paragraph_count}</p>
                  </div>
                  <div>
                    <p className="text-ios-gray">检测耗时</p>
                    <p className="font-semibold text-black">{(report.processing_time_ms / 1000).toFixed(1)}s</p>
                  </div>
                </div>
              </div>

              {/* LLM 信号 */}
              {report.llm.available && report.llm.signals.length > 0 && (
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

              {!report.llm.available && (
                <div className="text-[12px] text-ios-gray bg-gray-50 rounded-lg px-3 py-2 self-start">
                  LLM 评分不可用（未配置 API 或请求失败）<br />
                  当前结果仅基于文体特征
                </div>
              )}
            </div>

            {/* 风险提示 */}
            <div className="mt-4 pt-4 border-t border-current/10">
              <p className="text-[12px] text-ios-gray/80">
                ⚠️ 本检测结果仅供参考，不代表知网等商业系统的实际判定结果。建议分数≥60分时进行手动修改后再提交知网检测。
              </p>
            </div>
          </div>

          {/* ② 文体特征详情 */}
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
                {/* 两列特征条 */}
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

                {/* 统计数字 */}
                <div className="flex gap-4 pt-2 flex-wrap text-[13px] text-ios-gray border-t border-gray-100">
                  <span>句子：{report.stylometric.stats.sentence_count}</span>
                  <span>段落：{report.stylometric.stats.paragraph_count}</span>
                  <span>词元：{report.stylometric.stats.token_count}</span>
                </div>
              </div>
            )}
          </div>

          {/* ③ 段落分布 */}
          <div className="bg-white rounded-2xl shadow-ios overflow-hidden">
            <button
              onClick={() => setShowSections(v => !v)}
              className="w-full flex items-center justify-between p-5 hover:bg-gray-50 transition-colors"
            >
              <div className="flex items-center gap-3">
                <span className="text-[15px] font-bold text-black">段落风险分布</span>
                <div className="flex gap-2 text-[12px]">
                  {['significant', 'suspected', 'unmarked'].map(t => {
                    const cnt = report.sections.filter(s => s.tier === t).length;
                    if (cnt === 0) return null;
                    return (
                      <span key={t} className={`px-2 py-0.5 rounded-full border ${sectionTierColor(t)}`}>
                        {report.risk_legend[t]?.label} ×{cnt}
                      </span>
                    );
                  })}
                </div>
              </div>
              {showSections ? <ChevronUp className="w-5 h-5 text-ios-gray" /> : <ChevronDown className="w-5 h-5 text-ios-gray" />}
            </button>

            {showSections && (
              <div className="border-t border-gray-100 divide-y divide-gray-50">
                {report.sections.filter(s => s.tier !== 'skip').map((sec) => (
                  <div key={sec.index} className="flex items-start gap-3 px-5 py-3">
                    <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-gray-50 flex items-center justify-center text-[12px] font-bold text-ios-gray">
                      {sec.index + 1}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-[13px] text-gray-700 leading-relaxed line-clamp-2">{sec.text_preview}</p>
                      <div className="flex items-center gap-2 mt-1.5">
                        <span className={`text-[11px] px-2 py-0.5 rounded-full border ${sectionTierColor(sec.tier)}`}>
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

          {/* ④ 图例 */}
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
