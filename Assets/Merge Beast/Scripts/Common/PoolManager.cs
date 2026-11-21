using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.Events;
using Spine.Unity;

namespace MergeBeast
{
    public class PoolManager : MonoBehaviour
    {
        private static PoolManager _instance;
        public static PoolManager Instance => _instance;

        public List<FXDefine> _poolData;

        private Dictionary<EnumDefine.FXTYPE, Dictionary<int, List<ParticleSystem>>> _pool;

        public UnityAction<float, int> ActionLoading;

        [SerializeField] private List< SkeletonAnimation> _prfHit;
        private Dictionary<int,List< SkeletonAnimation>> _poolHits;


        // Use this for initialization
        private void Awake()
        {
            if (_instance == null) _instance = this;
            DontDestroyOnLoad(this.gameObject);
        }

        IEnumerator Start()
        {
            _pool = new Dictionary<EnumDefine.FXTYPE, Dictionary<int, List<ParticleSystem>>>();
            int total = 0;
            for (int t = 0; t < _poolData.Count; t++)
            {
                total += _poolData[t].Particles.Count * _poolData[t].Amount;
            }

            float count = 0f;
            for (int t = 0; t < _poolData.Count; t++)
            {
                Dictionary<int, List<ParticleSystem>> pol = new Dictionary<int, List<ParticleSystem>>();
                GameObject obj = new GameObject($"{_poolData[t].Name}");
                obj.transform.SetParent(this.transform);
                obj.transform.localPosition = Vector3.zero;

                for (int i = 0; i < _poolData[t].Particles.Count; i++)
                {
                    List<ParticleSystem> listParticle = new List<ParticleSystem>();
                    for (int j = 0; j < _poolData[t].Amount; j++)
                    {
                        ParticleSystem particle = Instantiate(_poolData[t].Particles[i], obj.transform);
                        listParticle.Add(particle);
                        particle.gameObject.SetActive(false);

                        count++;
                        ActionLoading?.Invoke(count, total);
                            yield return null;
                    }
                    pol.Add(i, listParticle);
                }

                _pool.Add(_poolData[t].FxType, pol);
            }

            GameObject poolHit = new GameObject("Pool Hit");
            poolHit.transform.SetParent(this.transform);
            _poolHits = new Dictionary<int,List< SkeletonAnimation>>();
            for(int i = 0; i < _prfHit.Count; i++)
            {
                List<SkeletonAnimation> fxs = new List<SkeletonAnimation>();
                for (int j = 0; j < 5; j++)
                {
                    SkeletonAnimation skel = Instantiate(_prfHit[i], poolHit.transform);
                    fxs.Add(skel);
                    skel.gameObject.SetActive(false);
                    yield return new WaitForEndOfFrame();
                }
                _poolHits.Add(i, fxs);
            }

            float timeCountAds = 0f;
            while(timeCountAds < 3f )
            {
                timeCountAds += Time.deltaTime;
                // AdsManager 不存在时（场景里没挂）原来会直接空引用，异常抛在协程里会让
                // 下面的 LoadSceneAsync 永远执行不到，表现就是「一直卡在加载页」。
                if (AdsManager.Instance != null && AdsManager.Instance.IsLoaded())
                {
                    timeCountAds = 10;
                }
                yield return null;
            }

            AsyncOperation asyncLoad = SceneManager.LoadSceneAsync(StringDefine.SCENE_MAIN, LoadSceneMode.Single);
            asyncLoad.allowSceneActivation = true;
            yield return asyncLoad;

        }

        public void PlayFXGetHit(int id, Vector2 position)
        {
            //    var pool = _pool[EnumDefine.FXTYPE.GET_HIT];
            //    this.PlayFX(id, position, pool);

            if (_poolHits == null || _poolHits.Count == 0) return;

            List<SkeletonAnimation> fxs = _poolHits[Random.Range(0, _poolHits.Count)];
            for(int i = 0; i < fxs.Count; i++)
            {
                if (!fxs[i].gameObject.activeInHierarchy)
                {
                    fxs[i].gameObject.SetActive(true);
                    fxs[i].transform.position = position;

                    fxs[i].AnimationState.Complete += delegate {
                        fxs[i].gameObject.SetActive(false);
                    };

                    return;
                }
            }
        }


        public void PlayFXHealHP( Vector2 position)
        {
            this.PlayFX(0, position, GetFxPool(EnumDefine.FXTYPE.HEALING_HP));
        }

        public void PlayFXEnemyDead(Vector3 postion)
        {
            this.PlayFX(0, postion, GetFxPool(EnumDefine.FXTYPE.ENEMY_DEAD));
        }

        public void PlayFXBeastMerge(int id, Vector2 postion)
        {
            this.PlayFX(id, postion, GetFxPool(EnumDefine.FXTYPE.BEAST_MERGE));
        }

        public void PlayFXNewBeast(int id)
        {
            this.PlayFX(id, Vector2.zero, GetFxPool(EnumDefine.FXTYPE.NEW_BEAST));
        }

        /// <summary>
        /// 取特效池。原来直接 _pool[type]，一旦该类型的特效没配进 _poolData，
        /// 或者 Start 协程还没跑完（_pool 还是 null），这里就抛 KeyNotFound / 空引用，
        /// 把调用方（战斗、结算逻辑）一起打断。
        /// </summary>
        private Dictionary<int, List<ParticleSystem>> GetFxPool(EnumDefine.FXTYPE type)
        {
            Dictionary<int, List<ParticleSystem>> pool;
            if (_pool != null && _pool.TryGetValue(type, out pool)) return pool;
            return null;
        }

        private void PlayFX(int id, Vector3 position, Dictionary<int, List<ParticleSystem>> pool)
        {
            if (pool == null || pool.Count == 0) return;

            int n = id % pool.Count;
            List<ParticleSystem> fxs;
            if (!pool.TryGetValue(n, out fxs) || fxs == null || fxs.Count == 0) return;

            for (int i = 0; i < fxs.Count; i++)
            {
                if (!fxs[i].gameObject.activeInHierarchy)
                {
                    fxs[i].gameObject.SetActive(true);
                    fxs[i].transform.position = position;
                    fxs[i].Play();
                    //fxs[i].enableEmission = true;
                    if(gameObject.activeSelf)
                        StartCoroutine(IETakeFX(fxs[i].main.duration, fxs[i].gameObject));
                    return;
                }
            }
        }

        private IEnumerator IETakeFX(float time,GameObject fx)
        {
            yield return new WaitForSeconds(time);
            fx.SetActive(false);
        }
    }

    [System.Serializable]
    public class FXDefine
    {
        public string Name;
        public int Amount;
        public EnumDefine.FXTYPE FxType;
        public List<ParticleSystem> Particles;
    }
}
