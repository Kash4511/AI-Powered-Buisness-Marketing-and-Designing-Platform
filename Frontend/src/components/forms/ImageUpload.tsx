import React, { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { X, UploadCloud, ArrowRight, ChevronLeft } from 'lucide-react'

const T = {
  bg:'#ffffff', bg2:'#f7f7f5', bg3:'#f0f0ec',
  dark:'#0a0a0a', bd:'rgba(0,0,0,0.08)', bd2:'rgba(0,0,0,0.15)',
  t1:'#111111', t2:'#666666', t3:'#aaaaaa',
} as const

const Styles = () => (
  <style>{`
    @import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,wght@0,700;0,900;1,700&family=Instrument+Sans:wght@400;500;600&display=swap');
    .imu-dropzone{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px;width:100%;aspect-ratio:3/4;border:1.5px dashed ${T.bd2};border-radius:12px;cursor:pointer;transition:all 0.2s;background:${T.bg2};color:${T.t3};font-family:'Instrument Sans',sans-serif;font-size:0.78rem;font-weight:500;}
    .imu-dropzone:hover,.imu-dropzone.active{border-color:${T.dark};background:#fff;color:${T.t1};}
    .imu-dropzone:hover svg,.imu-dropzone.active svg{color:${T.dark};}
    .imu-img-wrap{position:relative;width:100%;aspect-ratio:3/4;border-radius:12px;overflow:hidden;border:1.5px solid ${T.bd};}
    .imu-img-wrap img{width:100%;height:100%;object-fit:cover;}
    .imu-remove{position:absolute;top:8px;right:8px;width:26px;height:26px;border-radius:50%;background:rgba(0,0,0,0.7);color:#fff;border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:background 0.15s;}
    .imu-remove:hover{background:rgba(0,0,0,0.9);}
    .imu-btn-p{display:inline-flex;align-items:center;gap:7px;padding:12px 24px;background:${T.dark};color:#fff;border:none;border-radius:10px;font-family:'Instrument Sans',sans-serif;font-size:0.85rem;font-weight:600;cursor:pointer;transition:all 0.2s;}
    .imu-btn-p:hover{background:#2a2a2a;transform:translateY(-1px);box-shadow:0 6px 20px rgba(0,0,0,0.15);}
    .imu-btn-s{display:inline-flex;align-items:center;gap:6px;padding:11px 18px;background:none;border:1px solid ${T.bd2};border-radius:10px;font-family:'Instrument Sans',sans-serif;font-size:0.83rem;font-weight:500;color:${T.t2};cursor:pointer;transition:all 0.2s;}
    .imu-btn-s:hover{border-color:rgba(0,0,0,0.25);color:${T.t1};background:${T.bg2};}
    .imu-skip{display:inline-flex;align-items:center;gap:5px;padding:8px 14px;background:none;border:none;font-family:'Instrument Sans',sans-serif;font-size:0.78rem;color:${T.t3};cursor:pointer;transition:color 0.15s;}
    .imu-skip:hover{color:${T.t2};}
  `}</style>
)

interface Props {
  onImagesSelected: (images:File[])=>void
  onClose: ()=>void
}

const ImageUpload: React.FC<Props> = ({ onImagesSelected, onClose }) => {
  const [images, setImages]     = useState<File[]>([])
  const [previews, setPreviews] = useState<string[]>([])
  const [error, setError]       = useState<string|null>(null)

  const onDrop = useCallback((accepted:File[])=>{
    const next = [...images,...accepted].slice(0,3)
    setImages(next)
    setPreviews(next.map(f=>URL.createObjectURL(f)))
    setError(null)
  },[images])

  const { getInputProps, isDragActive, open } = useDropzone({
    onDrop,
    accept:{'image/*':['.jpeg','.jpg','.png','.webp']},
    maxSize:10*1024*1024,
    multiple:true,
    noClick:true,
  })

  const remove = (i:number) => {
    const ni=images.filter((_,j)=>j!==i)
    const np=previews.filter((_,j)=>j!==i)
    URL.revokeObjectURL(previews[i])
    setImages(ni); setPreviews(np)
  }

  const handleContinue = () => {
    if(images.length===0){setError('Please upload at least one image');return}
    setError(null); onImagesSelected(images)
  }

  const handleSkip = () => onImagesSelected([])

  return (
    <>
      <Styles/>
      <input {...getInputProps()} style={{display:'none'}}/>

      {/* HEADER */}
      <div style={{padding:'20px 28px',borderBottom:`1px solid ${T.bd}`,background:'#fff'}}>
        <div style={{fontFamily:"'Fraunces',serif",fontSize:'1rem',fontWeight:700,color:T.dark,letterSpacing:'-0.2px',marginBottom:3}}>
          Upload Architectural Images
        </div>
        <div style={{fontSize:'0.75rem',color:T.t3}}>
          Add up to 3 project photos. They'll be placed throughout your lead magnet for maximum visual impact.
        </div>
      </div>

      {/* BODY */}
      <div style={{padding:'24px 28px',background:'#fff'}}>
        {error&&(
          <div style={{marginBottom:16,fontSize:'0.8rem',color:'#b00020',background:'#fff2f2',border:'1px solid rgba(200,50,50,0.15)',borderRadius:9,padding:'10px 14px'}}>
            {error}
          </div>
        )}

        <div style={{display:'grid',gridTemplateColumns:'repeat(3,1fr)',gap:14}}>
          {[0,1,2].map(i=>(
            previews[i]
              ? (
                <div key={i} className="imu-img-wrap">
                  <img src={previews[i]} alt={`Upload ${i+1}`}/>
                  <button className="imu-remove" onClick={()=>remove(i)}><X size={12}/></button>
                  <div style={{position:'absolute',bottom:8,left:8,background:'rgba(0,0,0,0.6)',color:'#fff',fontSize:'0.62rem',fontWeight:600,borderRadius:4,padding:'2px 7px'}}>
                    Image {i+1}
                  </div>
                </div>
              ) : (
                <div
                  key={i}
                  className={`imu-dropzone${isDragActive?' active':''}`}
                  onClick={open}
                  role="button"
                  tabIndex={0}
                  onKeyDown={e=>e.key==='Enter'&&open()}
                  aria-label={`Upload image ${i+1}`}
                >
                  <UploadCloud size={28} style={{transition:'color 0.2s'}}/>
                  <span>Browse Files</span>
                  <span style={{fontSize:'0.65rem',color:T.t3}}>JPG, PNG, WEBP · max 10MB</span>
                </div>
              )
          ))}
        </div>

        {/* Tips */}
        <div style={{marginTop:20,background:T.bg2,border:`1px solid ${T.bd}`,borderRadius:10,padding:'14px 16px',display:'flex',alignItems:'flex-start',gap:10}}>
          <div style={{width:5,height:5,borderRadius:'50%',background:T.dark,flexShrink:0,marginTop:6}}/>
          <div style={{fontSize:'0.75rem',color:T.t2,lineHeight:1.6}}>
            <strong style={{color:T.t1,fontWeight:600}}>Tips for best results:</strong> Use high-resolution photos of completed projects. Landscape or portrait orientations both work well. Images are automatically cropped and placed by the AI layout engine.
          </div>
        </div>
      </div>

      {/* FOOTER */}
      <div style={{padding:'18px 28px',borderTop:`1px solid ${T.bd}`,display:'flex',alignItems:'center',justifyContent:'space-between',background:T.bg2}}>
        <div style={{display:'flex',alignItems:'center',gap:8}}>
          <button className="imu-btn-s" onClick={onClose}><ChevronLeft size={15}/> Back</button>
          <button className="imu-skip" onClick={handleSkip}>Skip images →</button>
        </div>
        <button className="imu-btn-p" onClick={handleContinue}>
          Generate PDF <ArrowRight size={14}/>
        </button>
      </div>
    </>
  )
}

export default ImageUpload