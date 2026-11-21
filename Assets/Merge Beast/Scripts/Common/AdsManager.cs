using UnityEngine;
using System;
using UnityEngine.Events;

namespace MergeBeast
{
    /// <summary>
    /// 广告桥（纯转发层）。
    ///
    /// 历史：这个类原来是 AppLovin MAX 的实现，游戏里（BatMan、FreeBoostCtrl、EnemyManager…）
    /// 到处在用 AdsManager.Instance.ShowAds / OnShowInter / IsLoaded。
    /// 现在工程只保留抖音小游戏 SDK，所以内部全部原样转发给 AdSDK 的 AdManager（TikTokPlatform），
    /// 对外 API 一个字都没改，调用方不需要动。
    ///
    /// 设计原则：**这里不做任何广告策略**。
    ///   · 展示时机、频次、加载、失败重试、暂停/恢复 timeScale，全部由抖音 SDK 负责；
    ///   · 抖音插屏本身有硬限制——广告模块启动 15 秒内不可展示、两次展示间隔不少于 30 秒
    ///     （见 TikTokPlatform.ShowInterstitialAd），我们在上层再叠一层秒表只会互相打架：
    ///     以前那个「统一 100 秒」的节流就是典型反例，把开局所有插屏点位全部堵死。
    ///
    /// 前置条件：场景里必须有 AdManager（AdSDK）实例，并填好 AppID 与激励视频/插屏广告位 ID。
    /// </summary>
    public class AdsManager : MonoBehaviour
    {
        private static AdsManager _instance;
        public static AdsManager Instance => _instance;

        private UnityAction _rewardAds;
        private bool _showing;

        public bool inited;

        /// <summary>
        /// 插屏总开关。世界地图（MapController）里会临时置 false，避免看地图时弹广告。
        /// </summary>
        public bool onInterestial = true;

        private void Awake()
        {
            if (_instance == null) _instance = this;
            DontDestroyOnLoad(this.gameObject);
        }

        void Start()
        {
            // 原来这里会向 http://45.77.248.145:6789/Analytics/user 明文上报
            // 包名 + SystemInfo.deviceUniqueIdentifier。Unity 2022 默认禁止 HTTP 明文请求，
            // 一启动就抛 InvalidOperationException: Insecure connection not allowed。
            // 这个接口是反编译源码里残留的第三方统计，与游戏玩法无关，已整体移除。

            if (DouyinAds == null)
            {
                Debug.LogWarning("[广告] 场景里没有 AdManager（AdSDK），广告将无法展示");
            }
        }

        /// <summary>
        /// 抖音的 AdManager 实例。用 Unity 的 == 重载判空，避免拿到「已销毁对象」。
        /// </summary>
        private static global::AdManager DouyinAds
        {
            get
            {
                var ad = global::AdManager.Instance;
                return ad == null ? null : ad;
            }
        }

        /// <summary>
        /// 抖音广告是「点播即加载」（创建实例时就已经 Load），没有可靠的预加载状态位可查，
        /// 所以固定返回 true：游戏里判断「有没有广告可看」的地方继续放行，
        /// 真正播不出来时由 SDK 的失败回调兜底。
        /// </summary>
        public bool IsLoaded(EnumDefine.ADSTYPE type = EnumDefine.ADSTYPE.Rewarded)
        {
            return true;
        }

        /// <summary>
        /// 插屏：只保留「世界地图不弹」这一个业务开关，其余全部交给抖音 SDK。
        /// 15 秒启动保护、30 秒间隔、加载状态判断都在 TikTokPlatform 里，这里不重复实现。
        /// </summary>
        public void OnShowInter()
        {
            if (!onInterestial) return;

            var ads = DouyinAds;
            if (ads == null)
            {
                Debug.LogWarning("[广告] 没有 AdManager（AdSDK）实例，插屏无法展示");
                return;
            }

            ads.ShowInterstitialAd();
        }

        /// <summary>
        /// 激励视频入口。参数保持与 MAX 版本一致，后两个历史参数目前不使用。
        /// 真正的播放走 AdManager.ShowRewardedVideoAd（抖音 SDK 内部负责暂停/恢复 timeScale、
        /// 判断是否看完、关闭后自动重建实例）。
        /// </summary>
        public void ShowAds(UnityAction callback, string keyEvent = null, EnumDefine.ADSTYPE adType = EnumDefine.ADSTYPE.Rewarded,
            bool required = true, EnumDefine.GameType gameType = EnumDefine.GameType.Beast)
        {
            // 插屏：BossComplete、EnemyManager 里有调用点，统一转发到抖音插屏。
            // 插屏没有「看完给奖励」的概念，callback 不触发。
            if (adType == EnumDefine.ADSTYPE.Interstitial)
            {
                OnShowInter();
                return;
            }

#if UNITY_EDITOR
            // 编辑器里 TTSDK 是 mock，广告拉不起来，直接发奖方便调试
            _showing = true;
            DailyQuestCtrl.Instane?.UpdateQuest(EnumDefine.DailyQuest.WatchAds);
            callback?.Invoke();
            _showing = false;
#else
            if (adType != EnumDefine.ADSTYPE.Rewarded)
            {
                return;
            }

            // 游戏内「免广告」道具 / VIP 免看广告：这是道具权益，不是广告策略，保留。
            bool removeAds = PlayerPrefs.GetInt(StringDefine.REMOVE_VIDEO_ADS, 0) == 1;
            float rate = CPlayer.GetVipConfig().percentIgnoreReward;
            int rand = new System.Random().Next(0, 100);
            if (removeAds || rate == 100 || rand < rate)
            {
                callback?.Invoke();
                UIManager.Instance?.ShowNotify("领取成功");
                _showing = false;
                return;
            }

            var ads = DouyinAds;
            if (ads == null)
            {
                Debug.LogWarning("[广告] 没有 AdManager（AdSDK）实例，看视频奖励无法发放");
                _showing = false;
                return;
            }

            _showing = true;
            _rewardAds = callback;
            ads.ShowRewardedVideoAd(OnRewarded, OnRewardFailed);
#endif
        }

        /// <summary>
        /// 激励视频看完：发奖 + 每日任务 + VIP 点数（与 MAX 版本的 OnRewardedAdReceivedRewardEvent 行为一致）。
        /// </summary>
        private void OnRewarded()
        {
            var cb = _rewardAds;
            _rewardAds = null;
            _showing = false;

            cb?.Invoke();
            DailyQuestCtrl.Instane?.UpdateQuest(EnumDefine.DailyQuest.WatchAds);
            CPlayer.AddVipPoint(1);
        }

        /// <summary>
        /// 没播完 / 加载失败：不发奖，把状态复位，避免 IsShowing() 一直为 true。
        /// </summary>
        private void OnRewardFailed(string message)
        {
            _rewardAds = null;
            _showing = false;

            Debug.LogWarning($"[广告] 激励视频未完成：{message}");
            UIManager.Instance?.ShowNotify("广告加载失败，请稍后再试");
        }

        public bool IsShowing()
        {
            return _showing;
        }
    }
}
