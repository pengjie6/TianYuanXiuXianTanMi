using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UI;

namespace MergeBeast
{
    /// <summary>
    /// 主界面「看广告领奖励」按钮（jiliBtn）。
    ///
    /// 流程：点击 → 按钮上原有的 UnityEvent 把场景里的 AdConfirm 弹窗激活 → 这里补挂「看完广告」的回调
    ///       → 激励视频播完 → 发放 500 宝石（顶部货币栏自动刷新）。
    ///
    /// 用运行时自动绑定而不是往场景里挂组件：Main.unity 有 1.6 万个 YAML 文档，
    /// 手工插组件容易破坏序列化，改由场景加载后按名字找按钮 AddComponent，零场景改动。
    /// </summary>
    public class JiliRewardButton : MonoBehaviour
    {
        /// <summary>看一次激励视频发放的宝石（钻石）数量。</summary>
        public const int REWARD_GEM = 500;

        /// <summary>按钮名（Main.unity 里的 GameObject 名）。</summary>
        private const string BUTTON_NAME = "jiliBtn";

        /// <summary>连点冷却，避免广告还没起来就重复挂回调。</summary>
        private const float CLICK_COOLDOWN = 1f;

        private Button _btn;
        private float _lastClickTime = -999f;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        private static void Install()
        {
            SceneManager.sceneLoaded -= OnSceneLoaded;
            SceneManager.sceneLoaded += OnSceneLoaded;
            TryAttach();
        }

        private static void OnSceneLoaded(Scene scene, LoadSceneMode mode)
        {
            TryAttach();
        }

        /// <summary>找到 jiliBtn 并挂上本组件（已挂过就跳过）。</summary>
        private static void TryAttach()
        {
            GameObject go = FindDeep(BUTTON_NAME);
            if (go == null) return;
            if (go.GetComponent<JiliRewardButton>() != null) return;

            go.AddComponent<JiliRewardButton>();
        }

        /// <summary>
        /// 全场景递归找同名节点（含未激活的父级）。
        /// GameObject.Find 只找激活链上的对象，主界面若被某个弹窗遮住而临时禁用就拿不到。
        /// </summary>
        private static GameObject FindDeep(string name)
        {
            Scene scene = SceneManager.GetActiveScene();
            if (!scene.IsValid()) return null;

            foreach (GameObject root in scene.GetRootGameObjects())
            {
                Transform t = FindIn(root.transform, name);
                if (t != null) return t.gameObject;
            }
            return null;
        }

        private static Transform FindIn(Transform parent, string name)
        {
            if (parent.name == name) return parent;

            for (int i = 0; i < parent.childCount; i++)
            {
                Transform hit = FindIn(parent.GetChild(i), name);
                if (hit != null) return hit;
            }
            return null;
        }

        private void Start()
        {
            _btn = GetComponent<Button>();
            if (_btn != null) _btn.onClick.AddListener(this.OnClick);
            else Debug.LogWarning($"[广告] {BUTTON_NAME} 上没有 Button 组件，领奖功能不可用");
        }

        private void OnDestroy()
        {
            if (_btn != null) _btn.onClick.RemoveListener(this.OnClick);
        }

        /// <summary>点击入口：把发奖回调挂到 AdConfirm 弹窗上（弹窗本身由按钮的 UnityEvent 打开）。</summary>
        public void OnClick()
        {
            if (Time.unscaledTime - _lastClickTime < CLICK_COOLDOWN) return;
            _lastClickTime = Time.unscaledTime;

            // Show 会把回调写到弹窗实例并显示弹窗；
            // 场景里那个 AdConfirm 若已被 UnityEvent 先激活，这里直接复用它，不会多开一个。
            AdConfirm.Show(OnRewarded);
        }

        /// <summary>激励视频播完：发 500 宝石。</summary>
        private void OnRewarded()
        {
            Utils.AddRubyCoin(REWARD_GEM);   // 内部会 PostEvent(OnUpDateMoney)，顶部宝石数量自动刷新
            UIManager.Instance?.ShowNotify($"获得 {REWARD_GEM} 宝石");
            Debug.Log($"[广告] 激励视频完成，发放 {REWARD_GEM} 宝石");
        }
    }
}
